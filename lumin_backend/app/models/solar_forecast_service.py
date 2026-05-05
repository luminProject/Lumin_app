"""
app/models/solar_forecast_service.py

SolarForecastService — determines the forecast case for a user and
sends notifications via DatabaseManager (DB insert) + FCMService (push).

Forecast Cases:
  no_panels          : user has no production device registered
  collecting         : device installed at the start of a season —
                       collecting data through the current season
  collecting_extended: device installed near the end of a season —
                       collection extends across two seasons to meet
                       the 45-day minimum threshold
  forecast_available : previous season data is complete (≥ 45 days) —
                       personalized forecast is ready for display
  feature_disabled   : device offline ≥ 15 days — forecast paused

Season definition:
  Based on Saudi Ministry of Environment official classification.
  Source: mewa.gov.sa — see Change Log v3, Section 3.3.
  Winter: December–February  |  Spring: March–May
  Summer: June–August        |  Autumn: September–November

Minimum collection threshold (45 days):
  Scientific basis: 80/20 train-test split on a ~90-day season.
  If < 45 days remain after installation, collection extends to next season.
  See Change Log v3, Section 3.4.

Design note:
  This service implements a runtime state-machine. The original class
  diagram defines SolarForecast with a single predicted_production_kwh
  float. Our implementation derives state from sensor_data and
  energycalculation tables without storing a separate status flag —
  consistent with the Observer pattern (state derived from data).
  See Change Log v3, Section 3.2.

  The α (personalized performance factor) is computed in the Flutter
  frontend to keep the backend stateless. It is never stored or exposed
  via API — it is an internal UI calculation only.
"""

from datetime import date, datetime, timezone
from typing import Optional
import calendar
import logging

from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#  SEASON CONSTANTS
# ═══════════════════════════════════════════════

SEASON_MAP: dict[int, str] = {
    12: "winter", 1: "winter",  2: "winter",
    3:  "spring", 4: "spring",  5: "spring",
    6:  "summer", 7: "summer",  8: "summer",
    9:  "autumn", 10: "autumn", 11: "autumn",
}

SEASON_MONTHS: dict[str, list[int]] = {
    "winter": [12, 1, 2],
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "autumn": [9, 10, 11],
}

SEASON_EMOJI: dict[str, str] = {
    "winter": "❄️",
    "spring": "🌸",
    "summer": "🌞",
    "autumn": "🍂",
}

SEASON_ORDER = ["winter", "spring", "summer", "autumn"]

# Minimum collected days in a season to generate a forecast
MIN_COLLECTION_DAYS  = 45

# Days offline before Solar Forecast is paused (must match device_monitor.py)
FEATURE_DISABLE_DAYS = 15

# Notification type identifiers
NOTIF_FORECAST_READY   = "forecast_ready"
NOTIF_DEVICE_WARNING   = "device_warning"
NOTIF_FEATURE_DISABLED = "feature_disabled"


# ═══════════════════════════════════════════════
#  CITY LOOKUP
# ═══════════════════════════════════════════════

_SAUDI_CITIES = [
    ("Makkah",  21.3891, 39.8579),
    ("Jeddah",  21.4858, 39.1925),
    ("Riyadh",  24.7136, 46.6753),
    ("Madinah", 24.5247, 39.5692),
    ("Dammam",  26.4207, 50.0888),
    ("Taif",    21.2854, 40.4147),
    ("Tabuk",   28.3838, 36.5550),
    ("Abha",    18.2164, 42.5053),
    ("Hail",    27.5114, 41.7208),
    ("Najran",  17.4923, 44.1277),
]


def _city_from_coords(lat, lon) -> str:
    """Return the nearest Saudi city name to the given coordinates."""
    if lat is None or lon is None:
        return ""
    best, best_d = "", float("inf")
    for name, clat, clon in _SAUDI_CITIES:
        d = (lat - clat) ** 2 + (lon - clon) ** 2
        if d < best_d:
            best_d, best = d, name
    return best


# ═══════════════════════════════════════════════
#  SEASON HELPERS
# ═══════════════════════════════════════════════

def get_current_season(d: date) -> str:
    """Return the season name for a given date."""
    return SEASON_MAP[d.month]


def get_season_bounds(season: str, ref_year: int) -> tuple[date, date]:
    """
    Return (start, end) dates for a season given its reference year.

    Winter spans two calendar years. ref_year is the year of Jan/Feb.
    Example: winter ref_year=2027 → Dec 2026 – Feb 2027.
    """
    months = SEASON_MONTHS[season]
    if season == "winter":
        start    = date(ref_year - 1, 12, 1)
        last_day = calendar.monthrange(ref_year, 2)[1]
        end      = date(ref_year, 2, last_day)
    else:
        start      = date(ref_year, months[0], 1)
        last_month = months[-1]
        last_day   = calendar.monthrange(ref_year, last_month)[1]
        end        = date(ref_year, last_month, last_day)
    return start, end


def get_previous_season(season: str) -> str:
    """Return the season that comes before the given one."""
    return SEASON_ORDER[(SEASON_ORDER.index(season) - 1) % 4]


def get_next_season(season: str) -> str:
    """Return the season that comes after the given one."""
    return SEASON_ORDER[(SEASON_ORDER.index(season) + 1) % 4]


def season_ref_year(season: str, today: date) -> int:
    """
    Return the reference year for a season.
    Winter in December belongs to next year's winter (ref_year = year + 1).
    All other seasons use the current calendar year.
    """
    if season == "winter" and today.month == 12:
        return today.year + 1
    return today.year


# ═══════════════════════════════════════════════
#  MAIN SERVICE
# ═══════════════════════════════════════════════

class SolarForecastService:
    """
    Determines the current forecast state for a user and dispatches
    forecast_ready notifications when a full season of data is available.
    """

    def __init__(self, supabase):
        self.db         = DatabaseManager(supabase)
        self._supabase  = supabase

    # ─────────────────────────────────────────
    #  PUBLIC: main entry point
    # ─────────────────────────────────────────

    def get_forecast_state(self, user_id: str, test_date: str = None) -> dict:
        """
        Compute and return the current forecast state for a user.

        Parameters
        ----------
        user_id   : str  — target user UUID
        test_date : str  — optional ISO date (YYYY-MM-DD) for testing

        Returns
        -------
        dict with `case` key and case-specific fields for the Flutter UI.
        """
        today = date.fromisoformat(test_date) if test_date else date.today()

        # ── 0. User location ──────────────────────────────────────────
        user_row = (
            self._supabase.table("users")
            .select("location, latitude, longitude")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ).data

        if user_row:
            raw_city = user_row[0].get("location")
            user_lat = user_row[0].get("latitude")
            user_lon = user_row[0].get("longitude")
            city     = raw_city or _city_from_coords(user_lat, user_lon)
        else:
            city, user_lat, user_lon = "", None, None

        # ── 1. Production device check ────────────────────────────────
        devices = (
            self._supabase.table("device")
            .select("device_id, panel_capacity, installation_date")
            .eq("user_id", user_id)
            .eq("device_type", "production")
            .execute()
        ).data

        if not devices:
            ghi_data = self._get_ghi_for_location(user_lat, user_lon)
            return {
                "case":                   "no_panels",
                "city":                   city,
                "avg_daily_ghi":          ghi_data["avg_daily_ghi"],
                "avg_monthly_production": ghi_data["avg_monthly_production"],
            }

        # ── 2. Device data ────────────────────────────────────────────
        device         = devices[0]
        device_id      = device["device_id"]
        panel_capacity = float(device.get("panel_capacity") or 5.0)

        raw_install       = device.get("installation_date")
        installation_date = (
            today if not raw_install
            else date.fromisoformat(str(raw_install).split("T")[0])
        )
        device_is_brand_new = (today == installation_date)

        # ── 3. Last sensor reading & days offline ─────────────────────
        last_readings = (
            self._supabase.table("sensor_data")
            .select("reading_time")
            .eq("device_id", device_id)
            .order("reading_time", desc=True)
            .limit(1)
            .execute()
        ).data

        last_reading_date: Optional[date] = None
        if last_readings:
            raw_rt            = last_readings[0]["reading_time"]
            last_reading_date = datetime.fromisoformat(
                str(raw_rt).split("+")[0].split("Z")[0]
            ).date()
            days_offline = max(0, (today - last_reading_date).days)
        else:
            days_offline = max(0, (today - installation_date).days)

        # ── 4. feature_disabled: offline ≥ 15 days ───────────────────
        if days_offline >= FEATURE_DISABLE_DAYS:
            return {
                "case":              "feature_disabled",
                "city":              city,
                "days_offline":      days_offline,
                "last_reading_date": last_reading_date.isoformat()
                                     if last_reading_date else None,
            }

        # ── 5. Current season bounds ──────────────────────────────────
        current_season           = get_current_season(today)
        ref_year                 = season_ref_year(current_season, today)
        season_start, season_end = get_season_bounds(current_season, ref_year)
        total_days               = (season_end - season_start).days + 1

        # ── 6. Collected days in current season ───────────────────────
        ec_rows = (
            self._supabase.table("energycalculation")
            .select("date, solar_production")
            .eq("user_id", user_id)
            .gte("date", season_start.isoformat())
            .lte("date", today.isoformat())
            .gt("solar_production", 0)
            .execute()
        ).data

        collected_days       = len(ec_rows)
        days_elapsed         = (today - season_start).days + 1
        effective_start      = max(installation_date, season_start)
        days_since_effective = (today - effective_start).days
        days_missed          = max(0, days_since_effective - collected_days)
        days_remaining       = (season_end - today).days

        # ── 7. Installation timing flags ──────────────────────────────
        install_in_current          = season_start <= installation_date <= today
        days_remaining_from_install = (season_end - installation_date).days

        # ── 8. Previous season ────────────────────────────────────────
        prev_season = get_previous_season(current_season)

        # Fix: use ref_year-1 only for winter. Winter spans two calendar
        # years, so its ref_year is the year of Jan/Feb, not Dec.
        # Using ref_year for spring (the old bug) caused spring to look
        # for winter data one year too early, returning no rows.
        prev_ref             = ref_year - 1 if current_season == "winter" else ref_year
        prev_start, prev_end = get_season_bounds(prev_season, prev_ref)

        prev_rows = (
            self._supabase.table("energycalculation")
            .select("date, solar_production")
            .eq("user_id", user_id)
            .gte("date", prev_start.isoformat())
            .lte("date", prev_end.isoformat())
            .gt("solar_production", 0)
            .execute()
        ).data
        has_prev_season_data = len(prev_rows) >= MIN_COLLECTION_DAYS

        # ── 9. Case determination ─────────────────────────────────────

        # ── forecast_available ────────────────────────────────────────
        if has_prev_season_data and not install_in_current:
            self._notify_forecast_ready(
                user_id=user_id,
                season=prev_season,
                emoji=SEASON_EMOJI[prev_season],
                season_key=f"{prev_season}_{prev_end.year}",
            )
            return {
                "case": "forecast_available",
                **self._build_base_payload(
                    city=city,
                    season=current_season,
                    season_start=season_start,
                    season_end=season_end,
                    collected_days=collected_days,
                    days_elapsed=days_elapsed,
                    days_missed=days_missed,
                    days_remaining=days_remaining,
                    total_days=total_days,
                    days_offline=days_offline,
                    last_reading_date=last_reading_date,
                    panel_capacity=panel_capacity,
                ),
                "prev_season":       prev_season,
                "prev_season_emoji": SEASON_EMOJI[prev_season],
                "prev_season_start": prev_start.isoformat(),
                "prev_season_end":   prev_end.isoformat(),
                "actual_by_month":   self._group_by_month(prev_rows),
            }

        # ── collecting_extended ───────────────────────────────────────
        install_in_prev            = prev_start <= installation_date <= prev_end
        days_rem_from_prev_install = (
            (prev_end - installation_date).days if install_in_prev else 999
        )
        days_since_install = (today - installation_date).days

        if install_in_prev and days_rem_from_prev_install < MIN_COLLECTION_DAYS:
            ec_rows_ext = (
                self._supabase.table("energycalculation")
                .select("date, solar_production")
                .eq("user_id", user_id)
                .gte("date", installation_date.isoformat())
                .lte("date", today.isoformat())
                .gt("solar_production", 0)
                .execute()
            ).data

            return {
                "case": "collecting_extended",
                **self._build_base_payload(
                    city=city,
                    season=prev_season,
                    season_start=prev_start,
                    season_end=prev_end,
                    collected_days=len(ec_rows_ext),
                    days_elapsed=(today - installation_date).days + 1,
                    days_missed=max(0, days_since_install - len(ec_rows_ext)),
                    # Fix: use season_end (next season end) not prev_end
                    # prev_end is already passed — days_remaining must count
                    # until the end of the NEXT season (where collection extends to)
                    days_remaining=max(0, (season_end - today).days),
                    total_days=(season_end - installation_date).days + 1,
                    days_offline=days_offline,
                    last_reading_date=last_reading_date or installation_date,
                    panel_capacity=panel_capacity,
                ),
                "display_start":               installation_date.isoformat(),
                "next_season":                 current_season,
                "next_season_emoji":           SEASON_EMOJI[current_season],
                "next_season_start":           season_start.isoformat(),
                "next_season_end":             season_end.isoformat(),
                "next_total_days":             total_days,
                "days_remaining_from_install": days_rem_from_prev_install,
            }

        if install_in_current and days_remaining_from_install < MIN_COLLECTION_DAYS:
            next_season          = get_next_season(current_season)
            next_ref             = ref_year + 1 if next_season == "winter" else ref_year
            next_start, next_end = get_season_bounds(next_season, next_ref)

            return {
                "case": "collecting_extended",
                **self._build_base_payload(
                    city=city,
                    season=current_season,
                    season_start=season_start,
                    season_end=season_end,
                    collected_days=collected_days,
                    days_elapsed=(today - installation_date).days + 1,
                    days_missed=max(0, days_since_install - collected_days),
                    days_remaining=max(0, (next_end - today).days),
                    total_days=(next_end - installation_date).days + 1,
                    days_offline=days_offline,
                    last_reading_date=last_reading_date or installation_date,
                    panel_capacity=panel_capacity,
                ),
                "display_start":               installation_date.isoformat(),
                "next_season":                 next_season,
                "next_season_emoji":           SEASON_EMOJI[next_season],
                "next_season_start":           next_start.isoformat(),
                "next_season_end":             next_end.isoformat(),
                "next_total_days":             (next_end - next_start).days + 1,
                "days_remaining_from_install": days_remaining_from_install,
            }

        # ── collecting ────────────────────────────────────────────────
        return {
            "case": "collecting",
            **self._build_base_payload(
                city=city,
                season=current_season,
                season_start=season_start,
                season_end=season_end,
                collected_days=collected_days,
                days_elapsed=days_elapsed,
                days_missed=days_missed,
                days_remaining=days_remaining,
                total_days=total_days,
                days_offline=days_offline,
                last_reading_date=last_reading_date or installation_date,
                panel_capacity=panel_capacity,
            ),
            "installation_date":   installation_date.isoformat(),
            "device_is_brand_new": device_is_brand_new,
        }

    # ─────────────────────────────────────────
    #  PRIVATE: shared payload builder
    # ─────────────────────────────────────────

    @staticmethod
    def _build_base_payload(
        city:              str,
        season:            str,
        season_start:      date,
        season_end:        date,
        collected_days:    int,
        days_elapsed:      int,
        days_missed:       int,
        days_remaining:    int,
        total_days:        int,
        days_offline:      int,
        last_reading_date: Optional[date],
        panel_capacity:    float,
    ) -> dict:
        """
        Build the fields shared across all collecting and forecast cases.
        Each case spreads this dict and adds its own unique fields.
        """
        return {
            "city":              city,
            "season":            season,
            "season_emoji":      SEASON_EMOJI[season],
            "season_start":      season_start.isoformat(),
            "season_end":        season_end.isoformat(),
            "collected_days":    collected_days,
            "days_elapsed":      days_elapsed,
            "days_missed":       days_missed,
            "days_remaining":    days_remaining,
            "total_days":        total_days,
            "days_offline":      days_offline,
            "last_reading_date": last_reading_date.isoformat()
                                 if last_reading_date else None,
            "panel_capacity":    panel_capacity,
        }

    # ─────────────────────────────────────────
    #  PRIVATE: forecast_ready notification
    # ─────────────────────────────────────────

    def _notify_forecast_ready(
        self,
        user_id:    str,
        season:     str,
        emoji:      str,
        season_key: str,
    ) -> None:
        """
        Send a forecast_ready notification once per season per user.

        Dedup: searches for an existing notification whose content ends
        with #{season_key} using ilike(). Sent at most once per season
        regardless of how many times get_forecast_state() is called.

        season_key format: {season_name}_{end_year}
        Example: winter_2027, spring_2027
        """
        try:
            logger.info(
                f"[SolarForecast] _notify_forecast_ready:"
                f" user={user_id} key=#{season_key}"
            )

            existing = (
                self._supabase.table("notification")
                .select("notification_id")
                .eq("user_id", user_id)
                .eq("notification_type", NOTIF_FORECAST_READY)
                .ilike("content", f"%#{season_key}")
                .limit(1)
                .execute()
            ).data

            if not existing:
                cap     = season.capitalize()
                content = (
                    f"Your {cap} {emoji} solar forecast is ready! "
                    f"View your personalized production predictions "
                    f"for the next 2 years. #{season_key}"
                )
                payload = {
                    "user_id":           user_id,
                    "notification_type": NOTIF_FORECAST_READY,
                    "content":           content,
                    "timestamp":         datetime.now(timezone.utc).isoformat(),
                }
                self.db.insert_notification(payload)

                # FCM push (fail-safe)
                try:
                    fcm_token = self.db.get_user_fcm_token(user_id)
                    if fcm_token:
                        FCMService.send_push(
                            fcm_token=fcm_token,
                            title="☀️ Solar Forecast Ready",
                            body=content[:100],
                        )
                except Exception:
                    pass

                logger.info(f"[SolarForecast] forecast_ready sent for #{season_key}")
            else:
                logger.info(
                    f"[SolarForecast] forecast_ready already sent"
                    f" for #{season_key}"
                )

        except Exception as e:
            logger.error(
                f"[SolarForecast] _notify_forecast_ready ERROR: {e}"
            )

    # ─────────────────────────────────────────
    #  PRIVATE: GHI fallback for no_panels
    # ─────────────────────────────────────────

    def _get_ghi_for_location(self, lat, lon) -> dict:
        """
        Return a regional GHI estimate for users without solar panels.

        Uses Saudi-average monthly GHI values (kWh/m²/day) with a
        standard 5 kWp reference system and PR = 0.78.

        Formula: E (kWh/month) = GHI_daily × PR × P_nom × 30
        Reference: IEC 61724-1, NREL PVWatts (Dobos 2014).

        Note: lat/lon accepted for future region-based GHI selection.
        """
        GHI_MONTHLY = {
             1: 4.14,  2: 5.01,  3: 6.02,  4: 6.71,  5: 7.14,
             6: 7.27,  7: 6.98,  8: 6.75,  9: 6.21, 10: 5.44,
            11: 4.52, 12: 3.89,
        }
        PR    = 0.78  # Performance Ratio (IEC 61724-1)
        P_NOM = 5.0   # Reference system size in kWp

        avg_ghi     = sum(GHI_MONTHLY.values()) / 12
        avg_monthly = avg_ghi * PR * P_NOM * 30

        return {
            "avg_daily_ghi":          round(avg_ghi, 2),
            "avg_monthly_production": round(avg_monthly, 1),
        }

    # ─────────────────────────────────────────
    #  PRIVATE: aggregate production by month
    # ─────────────────────────────────────────

    def _group_by_month(self, rows: list[dict]) -> dict[str, float]:
        """
        Aggregate solar_production values by month (YYYY-MM key).
        Used to build the actual_by_month chart data for forecast_available.
        """
        result: dict[str, float] = {}
        for row in rows:
            key    = row["date"][:7]
            result[key] = result.get(key, 0.0) + float(row["solar_production"] or 0)
        return result