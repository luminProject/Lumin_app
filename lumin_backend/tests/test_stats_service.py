"""
tests/test_stats_service.py
===========================
Unit tests for StatsService — energy data aggregation for the
Home screen statistics chart (Week / Month / Year).

WHY UNIT TESTS:
  StatsService aggregates energycalculation rows into chart points.
  These tests verify the aggregation math and structure WITHOUT
  a real Supabase connection — DatabaseManager is replaced with a mock.

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_stats_service.py -v
"""

import pytest
from unittest.mock import MagicMock
from app.models.stats_service import StatsService


# ── Helper: build a StatsService with mocked DB ───────────────────

def _make_service(rows):
    """
    Creates a StatsService whose db.get_energy_rows_for_range()
    returns the provided rows list.

    This lets each test control exactly what 'database' data exists
    without needing a real Supabase connection.
    """
    mock_supabase = MagicMock()
    service = StatsService(mock_supabase)
    service.db = MagicMock()
    service.db.get_energy_rows_for_range.return_value = rows
    return service


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: Week Aggregation
#
#  WHAT WE TEST:
#    The _get_week() method aggregates daily energycalculation rows
#    into 7 data points (Sat=0 → Fri=6).
#
#  WHY THIS MATTERS:
#    The Flutter chart expects exactly 7 points with labels
#    ["Sat","Sun","Mon","Tue","Wed","Thu","Fri"].
#    Wrong count or wrong labels = chart crashes or shows wrong data.
#    Missing days must return 0.0 (not null/error) to keep the chart
#    rendering even when no data exists for some days.
# ══════════════════════════════════════════════════════════════════

class TestWeekAggregation:

    def test_always_returns_exactly_7_points(self):
        # The chart always needs 7 points — one per day of the week.
        # Even if there is NO data at all, 7 zero-points must be returned.
        service = _make_service([])
        result  = service.get_stats("user-1", "week", "2026-05-05")
        assert len(result["points"]) == 7, \
            f"Expected 7 points, got {len(result['points'])}"

    def test_labels_are_sat_through_fri_in_order(self):
        # Saudi week starts on Saturday — labels must follow this order.
        # This matches how the Flutter chart renders the x-axis.
        service = _make_service([])
        result  = service.get_stats("user-1", "week", "2026-05-05")
        labels  = [p["label"] for p in result["points"]]
        assert labels == ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"], \
            f"Wrong labels: {labels}"

    def test_missing_day_returns_zero_not_null(self):
        # If no energycalculation row exists for a day, both solar and
        # grid must be 0.0 — not None, not an error.
        # This prevents the Flutter LineChart from crashing on null values.
        service = _make_service([])
        result  = service.get_stats("user-1", "week", "2026-05-05")
        for point in result["points"]:
            assert point["solar"] == 0.0, \
                f"Expected 0.0 for missing solar, got {point['solar']}"
            assert point["grid"] == 0.0, \
                f"Expected 0.0 for missing grid, got {point['grid']}"

    def test_saturday_data_goes_to_x0(self):
        # 2026-05-02 is a Saturday → must appear at x=0 (first point)
        # This verifies the week-start alignment logic is correct.
        rows = [{
            "date": "2026-05-02",
            "solar_production": 10.0,
            "total_consumption": 5.0
        }]
        service    = _make_service(rows)
        result     = service.get_stats("user-1", "week", "2026-05-02")
        sat_point  = result["points"][0]
        assert sat_point["x"]     == 0
        assert sat_point["solar"] == 10.0
        assert sat_point["grid"]  == 5.0

    def test_range_key_is_week(self):
        # The response must include the range type for the Flutter widget
        # to know which chart mode is active.
        service = _make_service([])
        result  = service.get_stats("user-1", "week", "2026-05-05")
        assert result["range"] == "week"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: Month Aggregation
#
#  WHAT WE TEST:
#    The _get_month() method groups daily rows into 4 weekly buckets:
#    W1 = days 1–7, W2 = 8–14, W3 = 15–21, W4 = 22–end of month.
#
#  WHY THIS MATTERS:
#    The Flutter chart for the Month view shows 4 bars (W1–W4).
#    Wrong bucket assignment = data shown in wrong week.
#    Wrong summing = data lost or duplicated in the chart.
# ══════════════════════════════════════════════════════════════════

class TestMonthAggregation:

    def test_always_returns_exactly_4_points(self):
        # Month view always needs 4 weekly buckets — even with no data.
        service = _make_service([])
        result  = service.get_stats("user-1", "month", "2026-05")
        assert len(result["points"]) == 4

    def test_labels_are_w1_through_w4(self):
        # Labels must be W1, W2, W3, W4 in order.
        service = _make_service([])
        result  = service.get_stats("user-1", "month", "2026-05")
        labels  = [p["label"] for p in result["points"]]
        assert labels == ["W1", "W2", "W3", "W4"]

    def test_days_1_to_7_go_to_w1(self):
        # Two rows in the first week (days 1 and 7) must BOTH land in W1.
        # Values must be SUMMED (not averaged, not overwritten).
        rows = [
            {"date": "2026-05-01", "solar_production": 5.0,  "total_consumption": 3.0},
            {"date": "2026-05-07", "solar_production": 5.0,  "total_consumption": 3.0},
        ]
        service = _make_service(rows)
        result  = service.get_stats("user-1", "month", "2026-05")
        w1      = result["points"][0]
        assert w1["label"] == "W1"
        assert w1["solar"] == 10.0, f"Expected W1 solar=10.0, got {w1['solar']}"
        assert w1["grid"]  == 6.0,  f"Expected W1 grid=6.0, got {w1['grid']}"

    def test_day_22_goes_to_w4(self):
        # Day 22 is the start of W4 (days 22–end of month).
        rows = [{"date": "2026-05-25", "solar_production": 8.0, "total_consumption": 4.0}]
        service = _make_service(rows)
        result  = service.get_stats("user-1", "month", "2026-05")
        w4      = result["points"][3]
        assert w4["label"] == "W4"
        assert w4["solar"] == 8.0
        assert w4["grid"]  == 4.0

    def test_empty_month_returns_all_zeros(self):
        # A month with no data must return four zero-buckets.
        service = _make_service([])
        result  = service.get_stats("user-1", "month", "2026-05")
        for point in result["points"]:
            assert point["solar"] == 0.0
            assert point["grid"]  == 0.0


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: Year Aggregation
#
#  WHAT WE TEST:
#    The _get_year() method groups daily rows into 12 monthly totals.
#    Jan=index 0, Feb=index 1, ..., Dec=index 11.
#
#  WHY THIS MATTERS:
#    The Flutter chart for Year view shows 12 data points (Jan–Dec).
#    Wrong month index = data shown in wrong month on the chart.
#    Multiple rows in the same month must be SUMMED correctly.
# ══════════════════════════════════════════════════════════════════

class TestYearAggregation:

    def test_always_returns_exactly_12_points(self):
        # Year view always needs 12 monthly points — even with no data.
        service = _make_service([])
        result  = service.get_stats("user-1", "year", "2026")
        assert len(result["points"]) == 12

    def test_labels_are_jan_through_dec(self):
        # Labels must be the 3-letter month abbreviations in order.
        service  = _make_service([])
        result   = service.get_stats("user-1", "year", "2026")
        labels   = [p["label"] for p in result["points"]]
        expected = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]
        assert labels == expected

    def test_may_data_goes_to_index_4(self):
        # May is month 5 → must appear at x=4 (0-indexed: Jan=0, May=4)
        # Verifies month-to-index mapping is correct.
        rows = [{"date": "2026-05-15", "solar_production": 20.0, "total_consumption": 12.0}]
        service = _make_service(rows)
        result  = service.get_stats("user-1", "year", "2026")
        may     = result["points"][4]
        assert may["label"] == "May"
        assert may["solar"] == 20.0
        assert may["grid"]  == 12.0

    def test_multiple_rows_same_month_are_summed(self):
        # Two rows in June must be SUMMED into one monthly total.
        # This is the most common real-world case: 30 rows per month.
        rows = [
            {"date": "2026-06-10", "solar_production": 15.0, "total_consumption": 8.0},
            {"date": "2026-06-20", "solar_production": 10.0, "total_consumption": 5.0},
        ]
        service = _make_service(rows)
        result  = service.get_stats("user-1", "year", "2026")
        june    = result["points"][5]
        assert june["label"] == "Jun"
        assert june["solar"] == 25.0, f"Expected 25.0, got {june['solar']}"
        assert june["grid"]  == 13.0, f"Expected 13.0, got {june['grid']}"

    def test_empty_year_returns_all_zeros(self):
        # A year with no data must return 12 zero-points.
        service = _make_service([])
        result  = service.get_stats("user-1", "year", "2026")
        for point in result["points"]:
            assert point["solar"] == 0.0
            assert point["grid"]  == 0.0


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 4: Input Validation & Structure
#
#  WHAT WE TEST:
#    - Invalid range_type raises ValueError
#    - Every point has all required keys: x, solar, grid, label
#    - x values are sequential starting from 0
#
#  WHY THIS MATTERS:
#    The Flutter widget accesses p['x'], p['solar'], p['grid'], p['label']
#    directly. A missing key causes a runtime crash in Flutter.
#    The ValueError ensures the API returns a 400 error instead of
#    silently returning wrong data for an unknown range type.
# ══════════════════════════════════════════════════════════════════

class TestValidationAndStructure:

    def test_invalid_range_type_raises_value_error(self):
        # 'daily' is not a valid range — must raise ValueError
        # In main.py this becomes an HTTP 400 response
        service = _make_service([])
        with pytest.raises(ValueError, match="Invalid range_type"):
            service.get_stats("user-1", "daily", "2026-05-05")

    def test_every_point_has_required_keys(self):
        # Each point dict must have x, solar, grid, label.
        # Missing any key = Flutter runtime crash.
        service = _make_service([])
        for range_type, anchor in [
            ("week", "2026-05-05"),
            ("month", "2026-05"),
            ("year", "2026"),
        ]:
            result = service.get_stats("user-1", range_type, anchor)
            for i, point in enumerate(result["points"]):
                for key in ["x", "solar", "grid", "label"]:
                    assert key in point, \
                        f"Point {i} in '{range_type}' missing key '{key}'"

    def test_x_values_are_sequential_from_zero(self):
        # x values must be 0, 1, 2, ... for the Flutter chart to
        # position data points correctly on the x-axis.
        service = _make_service([])
        for range_type, anchor in [
            ("week", "2026-05-05"),
            ("month", "2026-05"),
            ("year", "2026"),
        ]:
            result = service.get_stats("user-1", range_type, anchor)
            x_vals = [p["x"] for p in result["points"]]
            expected = list(range(len(x_vals)))
            assert x_vals == expected, \
                f"'{range_type}' x values {x_vals} != {expected}"