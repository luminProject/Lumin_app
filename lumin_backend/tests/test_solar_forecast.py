"""
tests/test_solar_forecast.py
============================
Unit tests for SolarForecastService — season helpers and state machine.

WHY UNIT TESTS:
  These tests verify pure logic functions and case routing WITHOUT
  connecting to Supabase or any external service. This means:
  - Tests run instantly (no network latency)
  - Tests are deterministic (no dependency on real data)
  - Each test isolates exactly one behaviour

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_solar_forecast.py -v
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

from app.models.solar_forecast_service import (
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
#  TEST CLASS 1: get_current_season()
#
#  WHAT WE TEST:
#    The month → season mapping based on Saudi Ministry of Environment
#    classification (mewa.gov.sa). Every month must map to exactly
#    one season — no month should be missing or double-mapped.
#
#  WHY THIS MATTERS:
#    If a month maps to the wrong season, the system will query the
#    wrong date range for collected data, causing wrong case routing.
#    Example: March mapped to winter instead of spring would cause
#    the system to look for winter data when it should look at spring.
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
#  WHAT WE TEST:
#    The start and end dates for each season given a reference year.
#    Winter is the critical case because it spans two calendar years:
#    Winter 2027 = December 2026 → February 2027.
#
#  WHY THIS MATTERS:
#    get_season_bounds() is used to query energycalculation rows.
#    Wrong bounds = wrong number of collected days = wrong case routing.
#    The 45-day threshold depends entirely on correct date ranges.
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
        # 45-day MIN_COLLECTION_DAYS threshold (80/20 split on 90 days).
        # See Change Log v4, Section 3.11.
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
#  TEST CLASS 3: get_previous_season() and get_next_season()
#
#  WHAT WE TEST:
#    The circular rotation of seasons. The order is:
#    winter → spring → summer → autumn → winter (wraps around)
#
#  WHY THIS MATTERS:
#    get_previous_season() is used to find what season to check for
#    completed data (to determine forecast_available).
#    Wrong rotation = checking the wrong season's data.
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
#  WHAT WE TEST:
#    The reference year calculation. Winter in December must use
#    next year as ref_year because December belongs to NEXT year's
#    winter (Dec 2026 is part of Winter 2027).
#
#  WHY THIS MATTERS:
#    This was the root cause of Bug#1 in the original implementation.
#    Using the wrong ref_year for winter caused the system to look up
#    season bounds one year too early, returning zero collected rows,
#    and therefore showing "collecting" instead of "forecast_available".
#    See Change Log v4, Section 3.10.
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
#  WHAT WE TEST:
#    The scientific threshold constants and the season-month mapping.
#
#  WHY THIS MATTERS:
#    MIN_COLLECTION_DAYS = 45 is the 80/20 split on a 90-day season.
#    FEATURE_DISABLE_DAYS = 15 must match device_monitor.py exactly.
#    If either constant changes without updating the Change Log, it
#    breaks the scientific justification documented in CL v4 §3.11.
#    This test acts as a "guardrail" against accidental changes.
# ══════════════════════════════════════════════════════════════════

class TestConstants:

    def test_min_collection_days_is_45(self):
        # 45 = 50% of ~90-day season (80/20 split basis)
        # Changing this requires updating Change Log v4 Section 3.11
        assert MIN_COLLECTION_DAYS == 45, (
            "MIN_COLLECTION_DAYS changed! Update Change Log v4 §3.11 "
            "with scientific justification before changing this value."
        )

    def test_feature_disable_days_is_15(self):
        # Must match FEATURE_DISABLE_DAYS in device_monitor.py
        # Both files use this constant — they must stay in sync
        assert FEATURE_DISABLE_DAYS == 15, (
            "FEATURE_DISABLE_DAYS changed! Ensure device_monitor.py "
            "uses the same value."
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
#  TEST CLASS 6: Case Routing (mocked Supabase)
#
#  WHAT WE TEST:
#    The SolarForecastService.get_forecast_state() case routing logic.
#    Supabase is replaced with MagicMock — no real DB connection needed.
#
#  WHY THIS MATTERS:
#    The 5 forecast cases (no_panels, collecting, collecting_extended,
#    forecast_available, feature_disabled) must route correctly based
#    on the data returned. Wrong routing = wrong UI shown to the user.
#
#  HOW MOCKING WORKS:
#    MagicMock replaces supabase.table().select().eq()...execute()
#    with a fake object that returns our test data. This lets us test
#    case routing without needing a real database.
# ══════════════════════════════════════════════════════════════════

class TestCaseRouting:

    def _make_chain(self, data):
        """
        Helper: creates a mock Supabase query chain that returns
        the given data list when .execute() is called.
        Any method call on the chain returns the chain itself
        (method chaining pattern used by Supabase client).
        """
        mock_result = MagicMock()
        mock_result.data = data
        chain = MagicMock()
        chain.execute.return_value = mock_result
        # All query methods return the chain itself (for chaining)
        for method in ["select", "eq", "gte", "lte", "gt", "order",
                       "limit", "ilike", "inFilter"]:
            getattr(chain, method).return_value = chain
        return chain

    def test_no_panels_case_when_no_production_device(self):
        """
        SCENARIO: User has no production device registered.
        EXPECTED: case = 'no_panels'
        WHY: Without a solar panel device, no data can be collected.
             The app should show regional GHI estimate instead.
        """
        from app.models.solar_forecast_service import SolarForecastService

        mock_supabase = MagicMock()

        # User exists with a location
        user_chain = self._make_chain([{
            "location": "Jeddah",
            "latitude": 21.49,
            "longitude": 39.19
        }])

        # No production devices found
        device_chain = self._make_chain([])

        def table_router(name):
            if name == "users":  return user_chain
            if name == "device": return device_chain
            return self._make_chain([])

        mock_supabase.table.side_effect = table_router

        service = SolarForecastService(mock_supabase)
        result  = service.get_forecast_state("test-user", test_date="2026-06-15")

        assert result["case"] == "no_panels", \
            f"Expected 'no_panels', got '{result['case']}'"

    def test_feature_disabled_when_offline_15_or_more_days(self):
        """
        SCENARIO: Device has been offline for exactly 15 days.
        EXPECTED: case = 'feature_disabled'
        WHY: After FEATURE_DISABLE_DAYS (15) consecutive days without
             a sensor reading, the Solar Forecast feature is paused.
             This protects users from seeing stale/misleading data.
        """
        from app.models.solar_forecast_service import SolarForecastService

        mock_supabase = MagicMock()

        user_chain = self._make_chain([{
            "location": "Riyadh",
            "latitude": 24.71,
            "longitude": 46.68
        }])

        device_chain = self._make_chain([{
            "device_id": 1,
            "panel_capacity": 5.0,
            "installation_date": "2026-01-01",
        }])

        # Last reading was 15 days ago (exactly at the disable threshold)
        sensor_chain = self._make_chain([{
            "reading_time": "2026-04-20T12:00:00"
        }])

        def table_router(name):
            if name == "users":       return user_chain
            if name == "device":      return device_chain
            if name == "sensor_data": return sensor_chain
            return self._make_chain([])

        mock_supabase.table.side_effect = table_router

        service = SolarForecastService(mock_supabase)
        # test_date = May 5 → days_offline = May5 - Apr20 = 15 days
        result  = service.get_forecast_state("test-user", test_date="2026-05-05")

        assert result["case"] == "feature_disabled", \
            f"Expected 'feature_disabled', got '{result['case']}'"
        assert result["days_offline"] >= FEATURE_DISABLE_DAYS

    def test_collecting_case_when_device_installed_start_of_season(self):
        """
        SCENARIO: Device installed at start of spring (March 1).
                  Today is March 20 — 19 days of data collected.
                  No previous season data exists.
        EXPECTED: case = 'collecting'
        WHY: Device is active, collecting data in the current season,
             but previous season has no data so forecast_available
             is not triggered. This is the normal early-stage state.
        """
        from app.models.solar_forecast_service import SolarForecastService

        mock_supabase = MagicMock()

        user_chain = self._make_chain([{
            "location": "Jeddah",
            "latitude": 21.49,
            "longitude": 39.19
        }])

        # Device installed March 1 — start of spring
        device_chain = self._make_chain([{
            "device_id": 2,
            "panel_capacity": 5.0,
            "installation_date": "2026-03-01",
        }])

        # Last reading was today (days_offline = 0)
        sensor_chain = self._make_chain([{
            "reading_time": "2026-03-20T12:00:00"
        }])

        # 19 rows in current season (spring 2026)
        ec_current = self._make_chain([
            {"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 15.0}
            for i in range(1, 20)
        ])

        # No data in previous season (winter) → no forecast_available
        ec_prev = self._make_chain([])

        call_count = {"ec": 0}

        def table_router(name):
            if name == "users":              return user_chain
            if name == "device":             return device_chain
            if name == "sensor_data":        return sensor_chain
            if name == "notification":       return self._make_chain([])
            if name == "energycalculation":
                call_count["ec"] += 1
                # First call = current season, second call = previous season
                return ec_current if call_count["ec"] == 1 else ec_prev
            return self._make_chain([])

        mock_supabase.table.side_effect = table_router

        service = SolarForecastService(mock_supabase)
        result  = service.get_forecast_state("test-user", test_date="2026-03-20")

        assert result["case"] == "collecting", \
            f"Expected 'collecting', got '{result['case']}'"
        assert result["collected_days"] == 19

    def test_forecast_available_when_previous_season_complete(self):
        """
        SCENARIO: Today is June 15 (summer). Previous season = spring.
                  Spring has 50 days of collected data (≥ 45 = complete).
                  Device was installed BEFORE current season started.
        EXPECTED: case = 'forecast_available'
        WHY: When the previous season has ≥ MIN_COLLECTION_DAYS (45) rows
             AND the device was not installed in the current season,
             the system has enough data to compute a personalized forecast.
             This is the target state users want to reach.
        """
        from app.models.solar_forecast_service import SolarForecastService

        mock_supabase = MagicMock()

        user_chain = self._make_chain([{
            "location": "Jeddah",
            "latitude": 21.49,
            "longitude": 39.19
        }])

        # Device installed in winter (before current summer season)
        device_chain = self._make_chain([{
            "device_id": 3,
            "panel_capacity": 5.0,
            "installation_date": "2026-01-15",
        }])

        # Last reading was today → days_offline = 0
        sensor_chain = self._make_chain([{
            "reading_time": "2026-06-15T12:00:00"
        }])

        # Current season (summer): only 15 days collected so far
        ec_current = self._make_chain([
            {"date": f"2026-06-{str(i).zfill(2)}", "solar_production": 15.0}
            for i in range(1, 16)
        ])

        # Previous season (spring): 50 days collected ≥ MIN_COLLECTION_DAYS
        ec_prev = self._make_chain([
            {"date": f"2026-03-{str(i).zfill(2)}", "solar_production": 15.0}
            for i in range(1, 46)
        ] + [
            {"date": f"2026-04-{str(i).zfill(2)}", "solar_production": 15.0}
            for i in range(1, 6)
        ])

        call_count = {"ec": 0}

        def table_router(name):
            if name == "users":              return user_chain
            if name == "device":             return device_chain
            if name == "sensor_data":        return sensor_chain
            if name == "notification":       return self._make_chain([])
            if name == "energycalculation":
                call_count["ec"] += 1
                return ec_current if call_count["ec"] == 1 else ec_prev
            return self._make_chain([])

        mock_supabase.table.side_effect = table_router

        service = SolarForecastService(mock_supabase)
        result  = service.get_forecast_state("test-user", test_date="2026-06-15")

        assert result["case"] == "forecast_available", \
            f"Expected 'forecast_available', got '{result['case']}'"
        assert "actual_by_month" in result, \
            "forecast_available must include 'actual_by_month' for the chart"
        assert result["prev_season"] == "spring"