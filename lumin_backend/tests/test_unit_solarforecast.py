"""
tests/test_unit_solarforecast.py

Unit Tests — Solar Forecast Feature
=====================================
Verifies pure logic functions and case routing in solar_forecast.py
WITHOUT connecting to Supabase, the XGBoost JSON file, or any
external service. DatabaseManager is replaced with MagicMock throughout.

Test classes:
  TestGetCurrentSeason   — month → season mapping (SEASON_MAP)
  TestGetSeasonBounds    — season start/end date calculation
  TestSeasonRotation     — get_previous_season() / get_next_season()
  TestSeasonRefYear      — winter ref_year boundary (Bug#1 regression)
  TestConstants          — MIN_COLLECTION_DAYS, FEATURE_DISABLE_DAYS, SEASON_MONTHS
  TestCaseRouting        — 5-case state machine (get_forecast_state)
  TestDeviceCheck        — device_warning / feature_disabled notification routing

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_unit_solarforecast.py -v
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from app.models.solar_forecast import (
    SolarForecast,
    get_current_season,
    get_season_bounds,
    get_previous_season,
    get_next_season,
    season_ref_year,
    SEASON_MONTHS,
    MIN_COLLECTION_DAYS,
    FEATURE_DISABLE_DAYS,
)


# ══════════════════════════════════════════════════════════════════
#  SHARED HELPER — used by TestCaseRouting and TestDeviceCheck
#  Single source of truth: if SolarForecast.__init__ changes,
#  only one method needs updating.
# ══════════════════════════════════════════════════════════════════

def _make_solar_service():
    """
    Builds a SolarForecast instance with a mocked DatabaseManager.

    Used by both TestCaseRouting and TestDeviceCheck.
    Single source of truth — if SolarForecast.__init__ changes,
    only this function needs updating.
    """
    svc = SolarForecast(MagicMock())
    svc.db = MagicMock()
    return svc


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: get_current_season()
#
#  Tests the month → season mapping (SEASON_MAP constant).
#  Every month must map to exactly one season — no gaps or duplicates.
#
#  Impact of failure: wrong season → wrong date range queried →
#  wrong collected_days count → wrong case returned to Flutter.
# ══════════════════════════════════════════════════════════════════

class TestGetCurrentSeason:

    def test_december_is_winter(self):
        # December is the START of winter (Dec–Feb)
        # Critical: winter spans two calendar years
        assert get_current_season(date(2026, 12, 1)) == "winter"

    def test_january_is_winter(self):
        # January is the MIDDLE of winter
        assert get_current_season(date(2026, 1, 15)) == "winter"

    def test_february_is_winter(self):
        # February is the END of winter
        assert get_current_season(date(2026, 2, 28)) == "winter"

    def test_march_is_spring(self):
        # March is the START of spring
        assert get_current_season(date(2026, 3, 1)) == "spring"

    def test_may_is_spring(self):
        # May is the END of spring
        assert get_current_season(date(2026, 5, 31)) == "spring"

    def test_june_is_summer(self):
        # June is the START of summer
        assert get_current_season(date(2026, 6, 1)) == "summer"

    def test_august_is_summer(self):
        # August is the END of summer
        assert get_current_season(date(2026, 8, 31)) == "summer"

    def test_september_is_autumn(self):
        # September is the START of autumn
        assert get_current_season(date(2026, 9, 1)) == "autumn"

    def test_november_is_autumn(self):
        # November is the END of autumn
        assert get_current_season(date(2026, 11, 30)) == "autumn"

    def test_all_12_months_return_valid_season(self):
        # Every single month must produce a known season name.
        # This catches any missing months in the SEASON_MAP constant.
        valid_seasons = {"winter", "spring", "summer", "autumn"}
        for month in range(1, 13):
            result = get_current_season(date(2026, month, 1))
            assert result in valid_seasons, \
                f"Month {month} returned unknown season: '{result}'"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: get_season_bounds()
#
#  Tests start/end date calculation for each season.
#  Winter is the critical case — it spans two calendar years:
#    Winter 2027 = December 2026 → February 2027
#
#  Impact of failure: wrong bounds → wrong energycalculation rows
#  fetched → wrong collected_days count → wrong case routing.
#  The 45-day threshold depends entirely on correct date ranges.
# ══════════════════════════════════════════════════════════════════

class TestGetSeasonBounds:

    def test_winter_start_is_december_of_previous_year(self):
        # Winter ref_year=2027 must START in December 2026 (previous year)
        start, _ = get_season_bounds("winter", 2027)
        assert start == date(2026, 12, 1)

    def test_winter_end_is_february_of_ref_year(self):
        # Winter ref_year=2027 must END in February 2027
        _, end = get_season_bounds("winter", 2027)
        assert end.month == 2
        assert end.year == 2027

    def test_spring_starts_march_same_year(self):
        # Spring always stays within one calendar year (March–May)
        start, end = get_season_bounds("spring", 2026)
        assert start == date(2026, 3, 1)
        assert end   == date(2026, 5, 31)

    def test_summer_starts_june_same_year(self):
        # Summer: June–August, all within same calendar year
        start, end = get_season_bounds("summer", 2026)
        assert start == date(2026, 6, 1)
        assert end   == date(2026, 8, 31)

    def test_autumn_starts_september_same_year(self):
        # Autumn: September–November, all within same calendar year
        start, end = get_season_bounds("autumn", 2026)
        assert start == date(2026, 9, 1)
        assert end   == date(2026, 11, 30)

    def test_season_is_approximately_90_days(self):
        # Each season is ~90 days. This is the scientific basis for the
        # 45-day MIN_COLLECTION_DAYS threshold (50% of a 90-day season).
        for season in ["spring", "summer", "autumn"]:
            start, end = get_season_bounds(season, 2026)
            days = (end - start).days + 1
            assert 89 <= days <= 92, \
                f"{season} has {days} days — expected ~90"

    def test_start_is_always_before_end(self):
        # Basic sanity check: start date must always precede end date
        for season in ["winter", "spring", "summer", "autumn"]:
            start, end = get_season_bounds(season, 2027)
            assert start < end, \
                f"{season}: start {start} is not before end {end}"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: get_previous_season() / get_next_season()
#
#  Tests the circular season rotation:
#    winter → spring → summer → autumn → winter (wraps)
#
#  Impact of failure: wrong previous season → wrong season's data
#  checked for ≥ 45 days → forecast_available triggered incorrectly
#  or missed entirely.
# ══════════════════════════════════════════════════════════════════

class TestSeasonRotation:

    def test_previous_of_spring_is_winter(self):
        assert get_previous_season("spring") == "winter"

    def test_previous_of_summer_is_spring(self):
        assert get_previous_season("summer") == "spring"

    def test_previous_of_autumn_is_summer(self):
        assert get_previous_season("autumn") == "summer"

    def test_previous_of_winter_wraps_to_autumn(self):
        # Winter is the first season — going back wraps to autumn
        # This tests the circular (% 4) rotation logic
        assert get_previous_season("winter") == "autumn"

    def test_next_of_winter_is_spring(self):
        assert get_next_season("winter") == "spring"

    def test_next_of_autumn_wraps_to_winter(self):
        # Autumn is the last season — going forward wraps to winter
        assert get_next_season("autumn") == "winter"

    def test_four_next_calls_return_to_start(self):
        # Going through 4 seasons must return to the original season
        # This proves the rotation is truly circular with no dead ends
        season = "spring"
        for _ in range(4):
            season = get_next_season(season)
        assert season == "spring"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 4: season_ref_year()
#
#  Tests the reference year logic. Winter in December must use
#  next year as ref_year — December 2026 is part of Winter 2027.
#
#  Bug#1 regression: the original implementation used the current year
#  for December, causing season bounds to be queried one year too early.
#  Result was zero collected rows → "collecting" shown instead of
#  "forecast_available". These tests lock that fix in place.
# ══════════════════════════════════════════════════════════════════

class TestSeasonRefYear:

    def test_winter_in_december_returns_next_year(self):
        # December 2026 is the start of Winter 2027
        # ref_year must be 2027 (next year), NOT 2026
        # This was the exact condition that triggered Bug#1
        result = season_ref_year("winter", date(2026, 12, 15))
        assert result == 2027, (
            "Bug#1 regression: winter in December must use ref_year = year+1. "
            f"Got {result}, expected 2027."
        )

    def test_winter_in_january_returns_same_year(self):
        # January 2027 is INSIDE Winter 2027 — ref_year is 2027 (same year)
        result = season_ref_year("winter", date(2027, 1, 10))
        assert result == 2027

    def test_winter_in_february_returns_same_year(self):
        # February 2027 is the END of Winter 2027 — ref_year is still 2027
        result = season_ref_year("winter", date(2027, 2, 15))
        assert result == 2027

    def test_spring_returns_same_year(self):
        # Spring stays within one calendar year — no year shift needed
        result = season_ref_year("spring", date(2026, 4, 1))
        assert result == 2026

    def test_summer_returns_same_year(self):
        result = season_ref_year("summer", date(2026, 7, 1))
        assert result == 2026

    def test_autumn_returns_same_year(self):
        result = season_ref_year("autumn", date(2026, 10, 1))
        assert result == 2026


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 5: Constants
#
#  Guards against accidental changes to threshold constants and
#  the season-month mapping.
#
#  MIN_COLLECTION_DAYS = 45  — 50% of a ~90-day season (IEC 61724-1)
#  FEATURE_DISABLE_DAYS = 15 — must match solar_forecast.py
#  SEASON_MONTHS             — all 12 months, each in exactly one season
# ══════════════════════════════════════════════════════════════════

class TestConstants:

    def test_min_collection_days_is_45(self):
        "MIN_COLLECTION_DAYS changed! This value requires scientific "
        "justification — 45 = 50% of a ~90-day season (IEC 61724-1)."
        assert MIN_COLLECTION_DAYS == 45, (
            
        )

    def test_feature_disable_days_is_15(self):
        "FEATURE_DISABLE_DAYS changed! Must stay consistent with "
        "solar_forecast.py FEATURE_DISABLE_DAYS constant."
        assert FEATURE_DISABLE_DAYS == 15, (
            
        )

    def test_all_12_months_covered_exactly_once(self):
        # Every month 1–12 must appear in exactly one season
        # No month should be missing or appear in two seasons
        all_months = []
        for months in SEASON_MONTHS.values():
            all_months.extend(months)
        assert sorted(all_months) == list(range(1, 13)), (
            "SEASON_MONTHS does not cover all 12 months exactly once. "
            f"Found: {sorted(all_months)}"
        )

    def test_each_season_has_exactly_3_months(self):
        # Each season must have exactly 3 months
        for season, months in SEASON_MONTHS.items():
            assert len(months) == 3, \
                f"{season} has {len(months)} months, expected 3"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 6: Case Routing
#
#  Tests get_forecast_state() case routing with a mocked DatabaseManager.
#  No real DB, Supabase, or XGBoost JSON file is needed.
#
#  Cases covered:
#    no_panels, feature_disabled, collecting,
#    collecting_extended, forecast_available
#  Boundary values tested:
#    days_offline 14 vs 15 (FEATURE_DISABLE_DAYS threshold)
#    collected_days 44 vs 45 (MIN_COLLECTION_DAYS threshold)
#
#  _get_ghi_for_location and _get_site_ghi are patched where needed
#  to avoid dependency on the XGBoost JSON file.
# ══════════════════════════════════════════════════════════════════
class TestCaseRouting:
    """
    Tests the 5-case state machine in SolarForecast.get_forecast_state().

    days_offline computation under test:
      Step 1 — get_today_solar_production(): if > 0 → days_offline = 0
      Step 2 — if 0 → get_latest_production_reading() to compute days_offline
      is_on is intentionally NOT used (wiring issues can give is_on=True + zero production).
    """

    def _make_service_with_db(self):
        """Delegates to module-level _make_solar_service() to avoid duplication."""
        return _make_solar_service()

    def test_no_panels_case_when_no_production_device(self):
        """
        SCENARIO: User has no production device registered.
        EXPECTED: case = 'no_panels'
        WHY: Without a solar panel, no data can be collected.
             The app shows a regional GHI estimate instead.
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Jeddah", "latitude": 21.49, "longitude": 39.19
        }
        service.db.get_production_device.return_value = None

        # _get_ghi_for_location calls _solar_model which requires the JSON file.
        # Mock it directly to isolate unit test from file system dependency.
        with patch.object(service, "_get_ghi_for_location",
                          return_value={"expected_this_month": 320.5}):
            result = service.get_forecast_state("test-user", test_date="2026-06-15")

        assert result["case"] == "no_panels"
        
        assert "expected_this_month" in result

    def test_feature_disabled_when_offline_15_or_more_days(self):
        """
        SCENARIO: No solar production today. Last reading was 15 days ago.
        EXPECTED: case = 'feature_disabled', days_offline >= 15

        Boundary value: FEATURE_DISABLE_DAYS = 15.
        Testing exactly at the threshold (15 days) confirms the >= condition.
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Riyadh", "latitude": 24.71, "longitude": 46.68
        }
        service.db.get_production_device.return_value = {
            "device_id": 1, "panel_capacity": 5.0,
            "installation_date": "2026-01-01",
        }
        # Step 1: no production today → proceed to check last_reading_at
        service.db.get_today_solar_production.return_value = 0.0
        # Step 2: latest reading was 2026-04-20 → days_offline = 15 (May 5 - Apr 20)
        service.db.get_latest_production_reading.return_value = \
            "2026-04-20T12:00:00+00:00"

        result = service.get_forecast_state("test-user", test_date="2026-05-05")

        assert result["case"] == "feature_disabled", \
            f"Expected 'feature_disabled', got '{result['case']}'"
        assert result["days_offline"] >= FEATURE_DISABLE_DAYS

    def test_feature_enabled_when_offline_14_days(self):
        """
        BOUNDARY VALUE: 14 days offline must NOT trigger feature_disabled.
        FEATURE_DISABLE_DAYS = 15, so 14 days should still allow normal case.
        This tests the boundary from below (one day before the threshold).
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Riyadh", "latitude": 24.71, "longitude": 46.68
        }
        service.db.get_production_device.return_value = {
            "device_id": 1, "panel_capacity": 5.0,
            "installation_date": "2026-01-01",
        }
        service.db.get_today_solar_production.return_value = 0.0
        # 14 days offline: May 4 - Apr 20 = 14 days
        service.db.get_latest_production_reading.return_value = \
            "2026-04-20T12:00:00+00:00"

        # Current season (spring) 4 rows, prev season (winter) 0 rows
        service.db.get_season_energy_rows.side_effect = [
            [{"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 10.0}
             for i in range(1, 5)],
            [],
        ]
        service.db.check_notification_exists.return_value = False

        result = service.get_forecast_state("test-user", test_date="2026-05-04")

        assert result["case"] != "feature_disabled", \
            "14 days offline should NOT trigger feature_disabled (threshold is 15)"
        assert result["days_offline"] == 14

    def test_collecting_case_when_device_installed_start_of_season(self):
        """
        SCENARIO: Device installed March 1. Today March 20.
                  19 days of production data collected.
                  No previous season data.
        EXPECTED: case = 'collecting', collected_days = 19
        WHY: Device is active (production > 0 today → days_offline = 0).
             Previous season has no data so forecast_available not triggered.
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Jeddah", "latitude": 21.49, "longitude": 39.19
        }
        service.db.get_production_device.return_value = {
            "device_id": 2, "panel_capacity": 5.0,
            "installation_date": "2026-03-01",
        }
        # Production > 0 today → days_offline = 0 (no need to check last_reading_at)
        service.db.get_today_solar_production.return_value = 15.0

        # 19 rows in current season (spring), 0 in previous (winter)
        ec_current = [
            {"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 15.0}
            for i in range(1, 20)
        ]
        service.db.get_season_energy_rows.side_effect = [
            ec_current,  # first call = current season
            [],          # second call = previous season (no data)
        ]
        service.db.check_notification_exists.return_value = False

        result = service.get_forecast_state("test-user", test_date="2026-03-20")

        assert result["case"] == "collecting", \
            f"Expected 'collecting', got '{result['case']}'"
        assert result["collected_days"] == 19

    def test_forecast_available_requires_exactly_45_days(self):
        """
        BOUNDARY VALUE: MIN_COLLECTION_DAYS = 45.
        44 days → NOT forecast_available.
        45 days → forecast_available.
        Tests both sides of the threshold.
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Jeddah", "latitude": 21.49, "longitude": 39.19
        }
        service.db.get_production_device.return_value = {
            "device_id": 3, "panel_capacity": 5.0,
            "installation_date": "2026-01-15",
        }
        service.db.get_today_solar_production.return_value = 15.0

        # 44 rows — one below threshold
        ec_current = [{"date": f"2026-06-{str(i).zfill(2)}", "solar_production": 15.0}
                      for i in range(1, 6)]
        ec_prev_44 = [{"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 15.0}
                      for i in range(1, 45)]  # 44 rows

        service.db.get_season_energy_rows.side_effect = [ec_current, ec_prev_44]
        service.db.check_notification_exists.return_value = False

        result_44 = service.get_forecast_state("test-user", test_date="2026-06-15")
        assert result_44["case"] != "forecast_available", \
            "44 days should NOT trigger forecast_available (threshold is 45)"

        # Reset and test with 45 rows — exactly at threshold
        service.db.get_user_fcm_token.return_value = None
        service.db.insert_notification.return_value = {}
        ec_prev_45 = [{"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 15.0}
                      for i in range(1, 46)]  # 45 rows

        service.db.get_season_energy_rows.side_effect = [ec_current, ec_prev_45]

        with patch.object(service, "_get_site_ghi", return_value={m: 6.0 for m in range(1, 13)}):
            result_45 = service.get_forecast_state("test-user", test_date="2026-06-15")

        assert result_45["case"] == "forecast_available", \
            "45 days should trigger forecast_available"

    def test_forecast_available_when_previous_season_complete(self):
        """
        SCENARIO: Today June 15 (summer). Previous season = spring.
                  Spring has 50 days of data (≥ 45 = MIN_COLLECTION_DAYS).
                  Device installed in winter (before current season).
        EXPECTED: case = 'forecast_available', prev_season = 'spring'
        WHY: Enough previous-season data exists to generate a personalized
             forecast. This is the target state for the feature.
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Jeddah", "latitude": 21.49, "longitude": 39.19
        }
        service.db.get_production_device.return_value = {
            "device_id": 3, "panel_capacity": 5.0,
            "installation_date": "2026-01-15",
        }
        service.db.get_today_solar_production.return_value = 15.0

        ec_current = [
            {"date": f"2026-06-{str(i).zfill(2)}", "solar_production": 15.0}
            for i in range(1, 16)
        ]
        ec_prev = (
            [{"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 15.0}
             for i in range(1, 46)] +
            [{"date": f"2026-04-{str(i).zfill(2)}", "solar_production": 15.0}
             for i in range(1, 6)]
        )  # 50 rows total
        service.db.get_season_energy_rows.side_effect = [ec_current, ec_prev]
        service.db.check_notification_exists.return_value = False
        service.db.insert_notification.return_value = {}
        service.db.get_user_fcm_token.return_value = None

        with patch.object(service, "_get_site_ghi", return_value={m: 6.0 for m in range(1, 13)}):
            result = service.get_forecast_state("test-user", test_date="2026-06-15")

        assert result["case"] == "forecast_available", \
            f"Expected 'forecast_available', got '{result['case']}'"
        assert result["prev_season"] == "spring"
        assert "actual_by_month" in result

    def test_collecting_extended_case(self):
        """
        SCENARIO: Device installed Feb 15 (near end of winter).
                  Remaining winter days from install = 13 days < MIN_COLLECTION_DAYS.
        EXPECTED: case = 'collecting_extended', next_season = 'spring'
        WHY: Not enough days left in the install season to collect 45 days,
             so collection extends into the next season.
        """
        service = self._make_service_with_db()

        service.db.get_user_location.return_value = {
            "location": "Jeddah", "latitude": 21.49, "longitude": 39.19
        }
        service.db.get_production_device.return_value = {
            "device_id": 4, "panel_capacity": 5.0,
            "installation_date": "2026-02-15",  # near end of winter
        }
        service.db.get_today_solar_production.return_value = 12.0

        ec_current = [
            {"date": f"2026-02-{str(i).zfill(2)}", "solar_production": 12.0}
            for i in range(15, 22)  # 7 rows
        ]
        service.db.get_season_energy_rows.side_effect = [
            ec_current,  # current season (winter)
            [],          # previous season (autumn) — no data
        ]
        service.db.check_notification_exists.return_value = False

        result = service.get_forecast_state("test-user", test_date="2026-02-21")

        assert result["case"] == "collecting_extended", \
            f"Expected 'collecting_extended', got '{result['case']}'"
        assert result["next_season"] == "spring"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 7: Device Check Methods
#
#  Tests check_user() and run_device_check() notification routing.
#  Device check logic lives in SolarForecast directly (not a separate class).
#
#  Notification types under test:
#    device_warning   — days_offline 1–14
#    feature_disabled — days_offline ≥ 15
#  Also tests:
#    dedup key prevents duplicate notifications
#    run_device_check() iterates all users exactly once
# ══════════════════════════════════════════════════════════════════

class TestDeviceCheck:
    """
    Tests for SolarForecast device check methods.
    self.db (DatabaseManager) is replaced with MagicMock — no real DB needed.
    """

    def _make_service(self):
        """Delegates to module-level _make_solar_service() to avoid duplication."""
        return _make_solar_service()

    def test_check_user_no_action_when_production_today(self):
        """
        SCENARIO: Device produced energy today (production > 0).
        EXPECTED: No notification sent — device is working fine.
        WHY: Step 1 short-circuit — no need to check last_reading_at.
        """
        svc = self._make_service()
        svc.db.get_today_solar_production.return_value = 12.5

        svc.check_user("test-user", test_date="2026-06-15")

        svc.db.insert_notification.assert_not_called()

    def test_check_user_sends_device_warning_when_offline_1_to_14_days(self):
        """
        SCENARIO: No production today. Last reading was 5 days ago.
        EXPECTED: device_warning notification sent (days 1–14).
        BOUNDARY VALUE: 5 days is well within the 1–14 range.
        """
        svc = self._make_service()
        svc.db.get_today_solar_production.return_value = 0.0
        svc.db.get_latest_production_reading.return_value = "2026-06-10T12:00:00+00:00"
        svc.db.get_production_device.return_value = {"installation_date": "2026-01-01"}
        svc.db.check_notification_exists.return_value = False
        svc.db.get_user_fcm_token.return_value = None
        svc.db.insert_notification.return_value = {}

        svc.check_user("test-user", test_date="2026-06-15")

        svc.db.insert_notification.assert_called_once()
        payload = svc.db.insert_notification.call_args[0][0]
        assert payload["notification_type"] == "device_warning"

    def test_check_user_sends_feature_disabled_at_15_days(self):
        """
        SCENARIO: No production. Last reading was exactly 15 days ago.
        EXPECTED: feature_disabled notification sent (boundary = FEATURE_DISABLE_DAYS).
        BOUNDARY VALUE: Tests at the exact threshold.
        """
        svc = self._make_service()
        svc.db.get_today_solar_production.return_value = 0.0
        svc.db.get_latest_production_reading.return_value = "2026-05-31T12:00:00+00:00"
        svc.db.get_production_device.return_value = {"installation_date": "2026-01-01"}
        svc.db.check_notification_exists.return_value = False
        svc.db.get_user_fcm_token.return_value = None
        svc.db.insert_notification.return_value = {}

        svc.check_user("test-user", test_date="2026-06-15")

        svc.db.insert_notification.assert_called_once()
        payload = svc.db.insert_notification.call_args[0][0]
        assert payload["notification_type"] == "feature_disabled"

    def test_check_user_dedup_prevents_duplicate_notification(self):
        """
        SCENARIO: Device offline 5 days. Notification already sent today.
        EXPECTED: No new notification inserted (dedup key exists).
        WHY: Prevents duplicate notifications if endpoint is called multiple times.
        """
        svc = self._make_service()
        svc.db.get_today_solar_production.return_value = 0.0
        svc.db.get_latest_production_reading.return_value = "2026-06-10T12:00:00+00:00"
        svc.db.get_production_device.return_value = {"installation_date": "2026-01-01"}
        # Dedup key already exists
        svc.db.check_notification_exists.return_value = True

        svc.check_user("test-user", test_date="2026-06-15")

        svc.db.insert_notification.assert_not_called()

    def test_run_device_check_iterates_all_users(self):
        """
        SCENARIO: 3 users have production devices.
        EXPECTED: _check_user_device called 3 times (once per user).
        WHY: run_device_check() is the scheduler entry point for all users.
        """
        svc = self._make_service()
        svc.db.get_all_production_devices.return_value = [
            {"user_id": "user-1"},
            {"user_id": "user-2"},
            {"user_id": "user-3"},
        ]
        svc.db.get_today_solar_production.return_value = 15.0

        svc.run_device_check()

        assert svc.db.get_today_solar_production.call_count == 3