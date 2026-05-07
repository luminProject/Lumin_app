"""
app/models/solar_forecast_service.py

SolarForecastService — state machine for the Solar Forecast feature.
See Change Log v4, Section 3.14.

days_offline logic:
  1. Check energycalculation for today's solar_production
  2. If 0 → get latest last_reading_at across ALL production devices
  3. Use that to compute days_offline (not is_on — wiring issues
     can cause is_on=True but zero production)

Notification:
  Uses Notification factories then DatabaseManager.insert_notification()
  + FCMService.send_push(). See Change Log v4, Sections 3.15 and 3.16.
"""

from datetime import date, datetime, timezone
from typing import Optional
import calendar
import logging

from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService
from app.models.notification import Notification

logger = logging.getLogger(__name__)

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
    if lat is None or lon is None:
        return ""
    best, best_d = "", float("inf")
    for name, clat, clon in _SAUDI_CITIES:
        d = (lat - clat) ** 2 + (lon - clon) ** 2
        if d < best_d:
            best_d, best = d, name
    return best


def get_current_season(d: date) -> str:
    return SEASON_MAP[d.month]


def get_season_bounds(season: str, ref_year: int) -> tuple[date, date]:
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
    if season == "winter" and today.month == 12:
        return today.year + 1
    return today.year


class SolarForecastService:

    def __init__(self, supabase):
        self.db = DatabaseManager(supabase)

    def get_forecast_state(self, user_id: str, test_date: str = None) -> dict:
        today = date.fromisoformat(test_date) if test_date else date.today()

        # ── 0. User location ──────────────────────────────────────────
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
                "case":                   "no_panels",
                "city":                   city,
                "avg_daily_ghi":          ghi_data["avg_daily_ghi"],
                "avg_monthly_production": ghi_data["avg_monthly_production"],
            }

        # ── 2. Device data ────────────────────────────────────────────
        device_id      = device["device_id"]
        panel_capacity = float(device.get("panel_capacity") or 5.0)
        raw_install    = device.get("installation_date")
        installation_date = (
            today if not raw_install
            else date.fromisoformat(str(raw_install).split("T")[0])
        )
        device_is_brand_new = (today == installation_date)

        # ── 3. days_offline ───────────────────────────────────────────
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
        total_days, days_offline, last_reading_date, panel_capacity,
    ) -> dict:
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

    def _notify_forecast_ready(
        self,
        user_id: str,
        season: str,
        emoji: str,
        season_key: str,
    ) -> None:
        """
        Send forecast_ready notification once per season per user.
        Dedup via content key. See Change Log v4, Section 3.16.
        """
        try:
            if self.db.check_notification_exists(
                user_id, "forecast_ready", f"#{season_key}"
            ):
                logger.info(
                    f"[SolarForecast] forecast_ready already sent for #{season_key}"
                )
                return

            notif = Notification.forForecastReady(
                user_id=user_id,
                season=season,
                emoji=emoji,
                season_key=season_key,
            )
            self.db.insert_notification(notif.build_db_payload())

            try:
                fcm_token = self.db.get_user_fcm_token(user_id)
                if fcm_token:
                    FCMService.send_push(
                        fcm_token=fcm_token,
                        title=notif.getPushTitle(),
                        body=notif.getPushBody(),
                    )
            except Exception:
                pass

            logger.info(f"[SolarForecast] forecast_ready sent for #{season_key}")

        except Exception as e:
            logger.error(f"[SolarForecast] _notify_forecast_ready ERROR: {e}")

    def _get_ghi_for_location(self, lat, lon) -> dict:
        GHI_MONTHLY = {
             1: 4.14,  2: 5.01,  3: 6.02,  4: 6.71,  5: 7.14,
             6: 7.27,  7: 6.98,  8: 6.75,  9: 6.21, 10: 5.44,
            11: 4.52, 12: 3.89,
        }
        avg_ghi     = sum(GHI_MONTHLY.values()) / 12
        avg_monthly = avg_ghi * 0.78 * 5.0 * 30
        return {
            "avg_daily_ghi":          round(avg_ghi, 2),
            "avg_monthly_production": round(avg_monthly, 1),
        }

    def _group_by_month(self, rows: list[dict]) -> dict[str, float]:
        result: dict[str, float] = {}
        for row in rows:
            key    = row["date"][:7]
            result[key] = result.get(key, 0.0) + float(row["solar_production"] or 0)
        return result