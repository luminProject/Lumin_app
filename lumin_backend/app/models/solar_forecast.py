"""
solar_forecast.py

SolarForecast — state machine for the Solar Forecast feature.

Determines which forecast case applies to a user and returns a
structured payload for the Flutter client to render.

Cases returned:
  no_panels          — user has no production device
  collecting         — active data collection, current season
  collecting_extended— collection spans two seasons (installed late)
  forecast_available — previous season has ≥ 45 days, forecast ready
  feature_disabled   — device offline ≥ 15 days

Key responsibilities:
  - get_forecast_state()  : main entry point, returns case + payload
  - run_device_check()    : batch check for all users (called by scheduler)
  - check_user()          : single-user device check (called per request)
  - _notify_forecast_ready(): sends forecast_ready push notification once per season
  - _get_site_ghi()       : fetches monthly GHI from XGBoost model for user location

Communicates with:
  - DatabaseManager  : all DB reads/writes
  - XGBoostSolarModel: GHI predictions per site/month/year
  - FCMService       : push notifications
  - Notification     : notification factory methods

days_offline logic:
  1. Check energycalculation for today's solar_production
  2. If 0 → get latest last_reading_at across all production devices
  3. Compute days_offline from that date (is_on is intentionally ignored —
     wiring issues can cause is_on=True with zero production)

forecast_available payload includes site_ghi — monthly GHI (kWh/m²/day)
from XGBoostSolarModel for the user's nearest site. Flutter uses this to
compute E_expected and E_personalized:
  E_expected     = (GHI / 1000) × PR × P_nom × days   
  α              = Σ E_actual / Σ E_expected            
  E_personalized = E_expected_future × α
"""
from datetime import date, datetime
from typing import Optional
import calendar
import logging

from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService
from app.models.notification import Notification
from app.models.xgboost_solar_model import XGBoostSolarModel

logger = logging.getLogger(__name__)

# ── Season helpers ────────────────────────────────────────────────────────────
# Single source of truth for month → season mapping (lowercase, used throughout).
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

MIN_COLLECTION_DAYS  = 45
FEATURE_DISABLE_DAYS = 15

# ── XGBoost singleton ─────────────────────────────────────────────────────────
# Loaded once at module import — JSON is read from disk a single time and
# kept in memory for the lifetime of the server process. All calls to
# _get_site_ghi() and _get_ghi_for_location() share this instance,
# avoiding repeated disk reads per request or per scheduled-job iteration.
_solar_model = XGBoostSolarModel()

# ── Saudi city lookup table ───────────────────────────────────────────────────
# Used only to resolve a display name when the DB location field is empty.
# Accuracy requirement is low (UI label only — GHI uses XGBoost Haversine).
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
    """
    Return the nearest city name to the given coordinates using Haversine distance.
    Used only as a fallback display label when the DB location field is empty.
    """
    if lat is None or lon is None:
        return ""
    import math
    best, best_d = "", float("inf")
    for name, clat, clon in _SAUDI_CITIES:
        phi1, phi2 = math.radians(lat), math.radians(clat)
        dphi = math.radians(clat - lat)
        dlam = math.radians(clon - lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        d = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        if d < best_d:
            best_d, best = d, name
    return best


def get_current_season(d: date) -> str:
    return SEASON_MAP[d.month]


def get_season_bounds(season: str, ref_year: int) -> tuple[date, date]:
    """
    Return (start, end) dates for a season given a reference year.
    Winter spans December of (ref_year - 1) through February of ref_year,
    so ref_year should be the year that contains January and February.
    For all other seasons, ref_year is the calendar year of the season.
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
    return SEASON_ORDER[(SEASON_ORDER.index(season) - 1) % 4]


def get_next_season(season: str) -> str:
    return SEASON_ORDER[(SEASON_ORDER.index(season) + 1) % 4]


def season_ref_year(season: str, today: date) -> int:
    """
    Return the reference year for a season.
    Winter is the only season that spans two calendar years (Dec–Feb).
    When today is in December, the winter season is considered to belong
    to the following year so that December and January share the same ref_year.
    """
    if season == "winter" and today.month == 12:
        return today.year + 1
    return today.year


class SolarForecast:

    def __init__(self, supabase):
        self.db = DatabaseManager(supabase)

    def get_forecast_state(self, user_id: str, test_date: str = None) -> dict:
        """
        Main entry point for the Solar Forecast feature.

        Input:
        user_id   : str  — target user UUID
        test_date : str  — optional YYYY-MM-DD override for today's date (used in tests)

        Output:
        dict with 'case' key and all fields required by the Flutter client
        for that case. See module docstring for case definitions.

        Processing:
        1. Resolve user location and city label
        2. Check for production device — if none, return no_panels
        3. Compute days_offline via solar_production and last_reading_at
        4. If days_offline >= 15 → feature_disabled
        5. Compute collected_days, days_missed, days_remaining for current season
        6. Check previous season for ≥ 45 days → forecast_available
        7. Check installation timing → collecting_extended if installed too late
        8. Default → collecting
        """
        
        # Validate test_date format early — raises ValueError with clear message
        # so main.py can return 422 instead of an opaque 500.
        if test_date:
            try:
                today = date.fromisoformat(test_date)
            except ValueError:
                raise ValueError(
                    f"Invalid test_date format: '{test_date}'. Expected YYYY-MM-DD."
                )
        else:
            today = date.today()

        # ── 0. User location ──────────────────────────────────────────
        # Note: DB errors propagate to main.py's outer try/except which
        # returns HTTP 500. No inner try needed here — keep it flat.
        location_row = self.db.get_user_location(user_id)
        if location_row:
            raw_city = location_row.get("location")
            user_lat = location_row.get("latitude")
            user_lon = location_row.get("longitude")
            city     = raw_city or _city_from_coords(user_lat, user_lon)
        else:
            city, user_lat, user_lon = "", None, None

        # ── 1. Production device check ────────────────────────────────
        device = self.db.get_production_device(user_id)
        if not device:
            ghi_data = self._get_ghi_for_location(user_lat, user_lon)
            return {
                "case":                "no_panels",
                "city":                city,
                "expected_this_month": ghi_data.get("expected_this_month"),
            }

        # ── 2. Device data ────────────────────────────────────────────
        panel_capacity      = float(device.get("panel_capacity") or 5.0)
        raw_install         = device.get("installation_date")
        installation_date   = (
            today if not raw_install
            else date.fromisoformat(str(raw_install).split("T")[0])
        )
        device_is_brand_new = (today == installation_date)

        # ── 3. days_offline ───────────────────────────────────────────
        # is_on is intentionally ignored — wiring issues can cause
        # is_on=True with zero production. last_reading_at is the
        # reliable indicator of actual device activity.
        last_reading_date: Optional[date] = None
        today_production = self.db.get_today_solar_production(user_id, today)

        if today_production > 0:
            days_offline      = 0
            last_reading_date = today
        else:
            raw_last = self.db.get_latest_production_reading(user_id)
            if raw_last:
                last_reading_date = datetime.fromisoformat(
                    str(raw_last).split("+")[0].split("Z")[0]
                ).date()
                days_offline = max(0, (today - last_reading_date).days)
            else:
                days_offline = max(0, (today - installation_date).days)

        # ── 4. feature_disabled ───────────────────────────────────────
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
        ec_rows              = self.db.get_season_energy_rows(user_id, season_start, today)
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
        prev_season          = get_previous_season(current_season)
        prev_ref             = ref_year - 1 if current_season == "winter" else ref_year
        prev_start, prev_end = get_season_bounds(prev_season, prev_ref)
        prev_rows            = self.db.get_season_energy_rows(user_id, prev_start, prev_end)
        has_prev_season_data = len(prev_rows) >= MIN_COLLECTION_DAYS

        # ── 9. Case determination ─────────────────────────────────────
        if has_prev_season_data and not install_in_current:
            self._notify_forecast_ready(
                user_id=user_id,
                season=prev_season,
                emoji=SEASON_EMOJI[prev_season],
                season_key=f"{prev_season}_{prev_end.year}",
            )

            # site_ghi: monthly GHI (kWh/m²/day) from XGBoost for the user's
            # nearest weather station. Replaces the hardcoded national average
            # in Flutter. Used to compute E_expected and E_personalized per
            # LUMIN_Formulas.pdf:
            #   E_expected     = (GHI / 1000) × PR × P_nom × days
            #   α              = Σ E_actual / Σ E_expected
            #   E_personalized = E_expected_future × α
            site_ghi = self._get_site_ghi(user_lat, user_lon, prev_end.year)

            return {
                "case": "forecast_available",
                **self._build_base_payload(
                    city=city, season=current_season,
                    season_start=season_start, season_end=season_end,
                    collected_days=collected_days, days_elapsed=days_elapsed,
                    days_missed=days_missed, days_remaining=days_remaining,
                    total_days=total_days, days_offline=days_offline,
                    last_reading_date=last_reading_date,
                    panel_capacity=panel_capacity,
                ),
                "prev_season":       prev_season,
                "prev_season_emoji": SEASON_EMOJI[prev_season],
                "prev_season_start": prev_start.isoformat(),
                "prev_season_end":   prev_end.isoformat(),
                "actual_by_month":   self._group_by_month(prev_rows),
                # Keys are month numbers as strings ("1"–"12") for JSON compatibility.
                "site_ghi":          {str(k): v for k, v in site_ghi.items()},
            }

        install_in_prev            = prev_start <= installation_date <= prev_end
        days_rem_from_prev_install = (
            (prev_end - installation_date).days if install_in_prev else 999
        )
        days_since_install = (today - installation_date).days

        if install_in_prev and days_rem_from_prev_install < MIN_COLLECTION_DAYS:
            ec_rows_ext = self.db.get_season_energy_rows(
                user_id, installation_date, today
            )
            return {
                "case": "collecting_extended",
                **self._build_base_payload(
                    city=city, season=prev_season,
                    season_start=prev_start, season_end=prev_end,
                    collected_days=len(ec_rows_ext),
                    days_elapsed=(today - installation_date).days + 1,
                    days_missed=max(0, days_since_install - len(ec_rows_ext)),
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
                    city=city, season=current_season,
                    season_start=season_start, season_end=season_end,
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

        return {
            "case": "collecting",
            **self._build_base_payload(
                city=city, season=current_season,
                season_start=season_start, season_end=season_end,
                collected_days=collected_days, days_elapsed=days_elapsed,
                days_missed=days_missed, days_remaining=days_remaining,
                total_days=total_days, days_offline=days_offline,
                last_reading_date=last_reading_date or installation_date,
                panel_capacity=panel_capacity,
            ),
            "installation_date":   installation_date.isoformat(),
            "device_is_brand_new": device_is_brand_new,
        }

    @staticmethod
    def _build_base_payload(
        city, season, season_start, season_end,
        collected_days, days_elapsed, days_missed, days_remaining,
        total_days, days_offline, last_reading_date, panel_capacity,) -> dict:
        """
        Builds the common fields shared across all cases that have a device.

        Input : all season/collection/device fields as keyword args
        Output: dict with city, season, season_emoji, season_start/end,
                collected_days, days_elapsed, days_missed, days_remaining,
                total_days, days_offline, last_reading_date, panel_capacity
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

    def _get_site_ghi(self, lat, lon, year: int) -> dict[int, float]:
        """
        Returns monthly GHI (kWh/m²/day) for the nearest XGBoost weather station.

        Input:
        lat  : float — user latitude
        lon  : float — user longitude
        year : int   — forecast year (2026–2028)

        Output:
        {1: ghi_jan, 2: ghi_feb, ..., 12: ghi_dec}
        Returns {} if coordinates are missing or the model raises an error.
        Flutter falls back to 6.0 kWh/m²/day per month if dict is empty.

        Processing:
        - Uses module-level _solar_model singleton (JSON loaded once at startup)
        - XGBoost JSON stores GHI in Wh/m²/day — divides by 1000 before returning
        - Nearest site resolved via Haversine across 41 Saudi weather stations
        """
        try:
            if lat is None or lon is None:
                return {}
            site   = _solar_model.getNearestSite(lat, lon)
            result = {}
            for m in range(1, 13):
                ghi_wh    = _solar_model.predict(site, m, year)
                result[m] = round(ghi_wh / 1000, 4)
            logger.info(f"[SolarForecast] site_ghi loaded — site={site}, year={year}")
            return result
        except (KeyError, ValueError, FileNotFoundError, OSError) as e:
            logger.warning(f"[SolarForecast] _get_site_ghi failed: {e} — Flutter will use national average fallback")
            return {}

    def _notify_forecast_ready(
        self,
        user_id: str,
        season: str,
        emoji: str,
        season_key: str,
    ) -> None:
        """
        Sends a forecast_ready push notification once per season per user.

        Input:
        user_id    : str — target user UUID
        season     : str — season name (e.g. 'spring')
        emoji      : str — season emoji for notification body
        season_key : str — dedup key, format: {season}_{year} (e.g. 'spring_2026')

        Output: None

        Processing:
        Checks notification table for existing entry with type='forecast_ready'
        and content key matching season_key before sending. Prevents duplicate
        notifications if get_forecast_state is called multiple times in the same season.
        """
        try:
            if self.db.check_notification_exists(
                user_id, "forecast_ready", f"#{season_key}"
            ):
                logger.info(f"[SolarForecast] forecast_ready already sent for #{season_key}")
                return

            notif = Notification.forForecastReady(
                user_id=user_id,
                season=season,
                emoji=emoji,
                season_key=season_key,
            )
            self._send_notification(notif)
            logger.info(f"[SolarForecast] forecast_ready sent for #{season_key}")

        except Exception as e:
            logger.error(f"[SolarForecast] _notify_forecast_ready ERROR: {e}")

    def _get_ghi_for_location(self, lat, lon) -> dict:
        """
        Returns estimated monthly production for the no_panels case.

        Input:
        lat : float — user latitude
        lon : float — user longitude

        Output:
        {"expected_this_month": float}  — estimated kWh for the current month
        Returns {} if coordinates are missing or the model raises an error.

        Processing:
        Computes E_expected for the current month using:
            E_expected = (GHI_daily / 1000) × PR × P_nom × days_in_month
        where:
            PR    = 0.78  (Saudi residential PV, IEC 61724-1)
            P_nom = 5.0 kWp (reference system, NREL PVWatts)
            GHI   = XGBoost prediction for nearest site, current month and year
        Uses module-level _solar_model singleton (JSON not re-read per call).
        """
        _PR   = 0.78
        _PNOM = 5.0
        _DAYS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30,
                 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

        if lat is None or lon is None:
            logger.warning("[SolarForecast] no_panels: no coordinates — skipping GHI")
            return {}

        try:
            current_month = date.today().month
            current_year  = date.today().year
            days          = _DAYS[current_month]

            site     = _solar_model.getNearestSite(lat, lon)
            ghi_kwh  = _solar_model.predict(site, current_month, current_year) / 1000
            expected = round(ghi_kwh * _PR * _PNOM * days, 1)

            logger.info(
                f"[SolarForecast] no_panels expected_this_month={expected} kWh"
                f" (site={site}, month={current_month}, year={current_year})"
            )
            return {"expected_this_month": expected}

        except (KeyError, ValueError, FileNotFoundError, OSError) as e:
            logger.warning(f"[SolarForecast] no_panels XGBoost failed: {e}")
            return {}

    def _group_by_month(self, rows: list[dict]) -> dict[str, float]:
        """
        Aggregates daily energycalculation rows into monthly solar_production totals.

        Input:
        rows : list[dict] — energycalculation rows with 'date' and 'solar_production'

        Output:
        {"YYYY-MM": float, ...} — total kWh per month
        """
        result: dict[str, float] = {}
        for row in rows:
            key    = row["date"][:7]
            result[key] = result.get(key, 0.0) + float(row["solar_production"] or 0)
        return result

        # ── Device Monitor — merged ───────────────────────────────────────────────
        # Device check logic lives here rather than in a separate class because:
        #   - It uses the same self.db already owned by SolarForecast
        #   - It uses Notification factories already used by SolarForecast
        #   - No new dependencies are introduced
        # The scheduler calls run_device_check() for all users daily.
        # main.py calls check_user() per-user on each forecast request.

    def run_device_check(self) -> None:
        """
        Batch device check for all users who have a production device.

        Input : none
        Output: none

        Processing:
        Fetches all production devices from DB, deduplicates by user_id,
        then calls _check_user_device() for each user.
        Called by APScheduler daily at 08:00 AM Saudi time (05:00 UTC).
        """
        today = date.today()
        logger.info(f"[DeviceCheck] Starting daily check — {today}")
        all_devices = self.db.get_all_production_devices()
        user_ids    = list({d["user_id"] for d in all_devices})
        logger.info(f"[DeviceCheck] Found {len(user_ids)} user(s) with production devices")
        for user_id in user_ids:
            try:
                self._check_user_device(user_id, today)
            except Exception as e:
                logger.error(f"[DeviceCheck] Error for user {user_id}: {e}")
        logger.info("[DeviceCheck] Daily check complete")

    def check_user(self, user_id: str, test_date: str = None) -> None:
        """
        Single-user device check, called per HTTP request before get_forecast_state().

        Input:
        user_id   : str — target user UUID
        test_date : str — optional YYYY-MM-DD override (used in tests)

        Output: none

        Processing:
        Delegates to _check_user_device(). Runs before get_forecast_state()
        on every GET /solar-forecast request so the notification fires on
        the same request that renders the UI.
        """
        today = date.fromisoformat(test_date) if test_date else date.today()
        logger.info(f"[DeviceCheck] check_user({user_id}) today={today}")
        self._check_user_device(user_id, today)

    def _check_user_device(self, user_id: str, today: date) -> None:
        """
        Core device check per user:
          Step 1 — Check today's solar_production. If > 0 → device OK → return.
          Step 2 — If 0 → get latest last_reading_at to compute days_offline.
          Step 3 — Send device_warning (1–14 days) or feature_disabled (≥ 15).

        is_on is NOT used — wiring issues can cause is_on=True + zero production.
        
        Input:
        user_id : str  — target user UUID
        today   : date — reference date

        Output: none

        Processing:
        Step 1 — Check today's solar_production via energycalculation.
                If > 0 → device is active → return early.
        Step 2 — If 0 → get last_reading_at from device table to compute days_offline.
                is_on is intentionally ignored — wiring issues can cause
                is_on=True with zero production.
        Step 3 — days_offline 1–14  → send device_warning  (once per day, dedup by date)
                days_offline >= 15 → send feature_disabled (once per offline cycle)
        
        """
        logger.info(f"  → user_id={user_id}")

        today_production = self.db.get_today_solar_production(user_id, today)
        if today_production > 0:
            logger.info(f"    ✓ Solar production confirmed today ({today_production} kWh) — OK")
            return

        raw_last = self.db.get_latest_production_reading(user_id)

        device = self.db.get_production_device(user_id)
        installation_date = today
        if device and device.get("installation_date"):
            installation_date = date.fromisoformat(
                str(device["installation_date"]).split("T")[0]
            )

        last_reading_date: Optional[date] = None
        if raw_last:
            last_reading_date = datetime.fromisoformat(
                str(raw_last).split("+")[0].split("Z")[0]
            ).date()
            days_offline = max(0, (today - last_reading_date).days)
        else:
            days_offline = max(0, (today - installation_date).days)

        logger.info(f"    production=0 today, days_offline={days_offline} (last_reading={last_reading_date})")

        if days_offline == 0:
            logger.info("    ⚠ Zero production but device read today — possible intermittent issue")
            return

        if days_offline >= FEATURE_DISABLE_DAYS:
            last_str    = last_reading_date.strftime("%Y%m%d") if last_reading_date else "00000000"
            offline_key = f"#offline_since_{last_str}"
            if not self.db.check_notification_exists(user_id, "feature_disabled", offline_key):
                notif = Notification.forFeatureDisabled(
                    user_id=user_id,
                    days_offline=days_offline,
                    last_reading_date_str=last_str,
                )
                self._send_notification(notif)
                logger.info(f"    🚫 Sent feature_disabled ({offline_key})")
            else:
                logger.info("    ℹ️  feature_disabled already sent for this cycle")
            return

        today_str = today.strftime("%Y%m%d")
        warn_key  = f"#warn_{today_str}"
        if not self.db.check_notification_exists(user_id, "device_warning", warn_key):
            notif = Notification.forDeviceWarning(
                user_id=user_id,
                days_offline=days_offline,
                today_str=today_str,
                feature_disable_days=FEATURE_DISABLE_DAYS,
            )
            self._send_notification(notif)
            logger.info(f"    ⚠️  Sent device_warning (day {days_offline}, {warn_key})")
        else:
            logger.info("    ℹ️  device_warning already sent today")

    def _send_notification(self, notif: Notification) -> None:
        """
        Persists a notification to the DB and attempts to send an FCM push.

        Input:
        notif : Notification — built via Notification factory methods

        Output: none

        Processing:
        Always writes to notification table first.
        FCM push is attempted only if the user has a registered FCM token.
        FCM failure is caught silently — DB write must never be blocked by
        a push delivery failure.
        """
        
        self.db.insert_notification(notif.build_db_payload())
        try:
            fcm_token = self.db.get_user_fcm_token(notif.user_id)
            if not fcm_token:
                logger.warning(
                    f"[SolarForecast] No FCM token for user {notif.user_id} "
                    f"— push skipped"
                )
                return
            FCMService.send_push(
                fcm_token=fcm_token,
                title=notif.getPushTitle(),
                body=notif.getPushBody(),
            )
            logger.info(
                f"[SolarForecast] Push sent — type={notif.notification_type} "
                f"user={notif.user_id}"
            )
        except Exception as e:
            logger.error(           # ← بدل pass
                f"[SolarForecast] FCM send FAILED — "
                f"type={notif.notification_type} user={notif.user_id} error={e}"
            )