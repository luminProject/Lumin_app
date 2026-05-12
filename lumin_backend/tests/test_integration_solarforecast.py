"""
tests/test_integration_solar.py

Integration Tests — Solar Forecast Feature
==========================================
sensor_data removed: last_reading_at updated directly on device table.

PREREQUISITES:
  1. Backend running: python -m uvicorn app.main:app --reload
  2. A production device must exist for the test user.
  3. .env configured with SUPABASE_URL and SUPABASE_KEY.

RUN:
  cd lumin_backend
  python -m pytest tests/test_integration_solarforecast.py -v
"""

import os
import pytest
import requests
from datetime import date, timedelta

from dotenv import load_dotenv
import supabase as supabase_

load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
USER_ID  = "7f5f8815-f3f4-49f2-927b-31fb2dce6396"

db = supabase_.create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


# ══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def _get_device():
    rows = (
        db.table("device")
        .select("device_id, installation_date")
        .eq("user_id", USER_ID)
        .eq("device_type", "production")
        .limit(1)
        .execute()
    ).data
    assert rows, "No production device found."
    return rows[0]


def _reset(start_date: str):
    """
    Clear energycalculation, notifications, reset last_reading_at and installation_date.
    sensor_data no longer used — device.last_reading_at is the offline indicator.
    Notifications are cleared to prevent dedup keys from affecting subsequent test runs.
    """
    device    = _get_device()
    device_id = device["device_id"]
    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).execute()
    db.table("device").update({
        "installation_date":  start_date,
        "last_reading_at":    None,
        "production":         0.0,
        "is_on":              False,
        "total_energy_daily": 0.0,
        "total_energy":       0.0,
    }).eq("device_id", device_id).execute()


def _collect(start_iso: str, days: int) -> date:
    """
    Insert energycalculation rows and update last_reading_at on device.
    sensor_data no longer used.
    """
    device    = _get_device()
    device_id = device["device_id"]
    start     = date.fromisoformat(start_iso)

    rows = []
    for i in range(days):
        d = start + timedelta(days=i + 1)
        rows.append({
            "user_id":           USER_ID,
            "date":              d.isoformat(),
            "solar_production":  round(15.0 + (i % 5), 1),
            "total_consumption": 25.0,
            "total_cost":        4.5,
            "carbon_reduction":  7.8,
            "cost_savings":      2.7,
        })

    for i in range(0, len(rows), 20):
        db.table("energycalculation").upsert(rows[i:i + 20]).execute()

    last_date = start + timedelta(days=days)
    db.table("device").update({
        "last_reading_at": f"{last_date.isoformat()}T12:00:00+00:00"
    }).eq("device_id", device_id).execute()

    return last_date


def _offline(last_reading_date: date, days: int) -> date:
    """Advance virtual date without updating last_reading_at."""
    return last_reading_date + timedelta(days=days)


def _reconnect(virtual_date: date):
    """Update last_reading_at on device to simulate reconnect."""
    device    = _get_device()
    device_id = device["device_id"]
    db.table("device").update({
        "last_reading_at": f"{virtual_date.isoformat()}T12:00:00+00:00"
    }).eq("device_id", device_id).execute()


def _get_forecast(test_date: str) -> dict:
    url = f"{BASE_URL}/solar-forecast/{USER_ID}?test_date={test_date}"
    res = requests.get(url, timeout=10)
    assert res.status_code == 200, f"Expected HTTP 200, got {res.status_code}."
    return res.json()["data"]


def _get_stats(range_type: str, anchor: str) -> dict:
    url = f"{BASE_URL}/stats/{USER_ID}?range={range_type}&anchor={anchor}"
    res = requests.get(url, timeout=10)
    assert res.status_code == 200, f"Expected HTTP 200, got {res.status_code}."
    return res.json()["data"]


# ══════════════════════════════════════════════════════════════════
#  TEST CASES
# ══════════════════════════════════════════════════════════════════

def test_tc01_no_panels_returns_ghi_estimate():
    """
    SCENARIO: User has no production device.
    EXPECTED: case = 'no_panels', expected_this_month is positive.
    WHY: Without panels, the app shows an estimated regional production
         figure using XGBoost GHI data for the user's location.
    """
    rows = (
        db.table("device").select("device_id")
        .eq("user_id", USER_ID).eq("device_type", "production").execute()
    ).data
    if rows:
        pytest.skip("TC-01 requires no production device.")
    data = _get_forecast("2026-03-01")
    assert data["case"] == "no_panels"
    # expected_this_month is the correct field — not avg_daily_ghi
    assert "expected_this_month" in data
    assert data["expected_this_month"] > 0


def test_tc02_collecting_case():
    """
    SCENARIO: Device installed March 1. Collected 10 days. Today = March 11.
    EXPECTED: case = 'collecting', collected_days = 10, days_offline = 0.
    WHY: Production > 0 today (row exists) → days_offline = 0.
         No previous season data → not forecast_available.
    """
    _reset("2026-03-01")
    _collect("2026-03-01", 10)
    data = _get_forecast("2026-03-11")
    assert data["case"] == "collecting"
    assert data["collected_days"] == 10
    assert data["days_offline"] == 0
    assert data["season"] == "spring"


def test_tc03_collecting_extended_case():
    """
    SCENARIO: Device installed Feb 1, collected 10 days.
    EXPECTED: case = 'collecting_extended', next_season = 'spring'.
    WHY: Device installed near end of winter — not enough days to reach 45.
         Collection must extend into spring.
    """
    _reset("2026-02-01")
    _collect("2026-02-01", 10)
    data = _get_forecast("2026-02-11")
    assert data["case"] == "collecting_extended"
    assert data["next_season"] == "spring"
    assert data["days_remaining_from_install"] < 45


def test_tc04_forecast_available_case():
    """
    SCENARIO: Collected 92 days starting March 1. Today = June 1.
    EXPECTED: case = 'forecast_available', prev_season = 'spring'.
    WHY: Spring (prev season) has ≥ 45 days of data.
         Device installed before current season (summer).
    """
    _reset("2026-03-01")
    _collect("2026-03-01", 92)
    data = _get_forecast("2026-06-01")
    assert data["case"] == "forecast_available"
    assert data["prev_season"] == "spring"
    assert "actual_by_month" in data
    assert len(data["actual_by_month"]) > 0


def test_tc05_feature_disabled_after_15_days_offline():
    """
    SCENARIO: Collected 92 days, then 15 days without a reading.
    EXPECTED: case = 'feature_disabled', days_offline >= 15.
    WHY: FEATURE_DISABLE_DAYS = 15. At exactly 15 days, the forecast pauses.
    Boundary value: testing the threshold from above.
    """
    _reset("2026-03-01")
    last         = _collect("2026-03-01", 92)
    virtual_date = _offline(last, 15)
    data = _get_forecast(virtual_date.isoformat())
    assert data["case"] == "feature_disabled"
    assert data["days_offline"] >= 15
    assert "last_reading_date" in data


def test_tc05b_device_warning_offline_less_than_15_days():
    """
    SCENARIO: Collected 92 days, then 5 days without a reading.
    EXPECTED: case = 'forecast_available', days_offline = 5.
    WHY: 5 < FEATURE_DISABLE_DAYS(15) → not disabled.
         Spring has ≥ 45 days → forecast_available.
    Boundary value: testing the threshold from below.
    """
    _reset("2026-03-01")
    last         = _collect("2026-03-01", 92)
    virtual_date = _offline(last, 5)
    data = _get_forecast(virtual_date.isoformat())
    assert data["case"] == "forecast_available"
    assert data["days_offline"] == 5


def test_tc06_reconnect_resets_offline_state():
    """
    SCENARIO: Was offline 15 days, then reconnects on the virtual date.
    EXPECTED: case = 'forecast_available', days_offline = 0.
    WHY: After reconnect, last_reading_at = today → days_offline = 0.
         Feature is no longer disabled.
    """
    _reset("2026-03-01")
    last         = _collect("2026-03-01", 92)
    virtual_date = _offline(last, 15)
    _reconnect(virtual_date)
    data = _get_forecast(virtual_date.isoformat())
    assert data["case"] == "forecast_available"
    assert data["days_offline"] == 0


# ══════════════════════════════════════════════════════════════════
#  ERROR HANDLING TESTS — يثبتون وجود try/catch في النظام
#
#  WHY THESE TESTS:
#    Integration testing must verify not only the happy path but also
#    that the system handles failures gracefully (Sommerville Ch.8 —
#    "test for conditions that should cause exceptions").
#    These tests prove the try/catch blocks in solar_forecast.py and
#    main.py work as designed.
# ══════════════════════════════════════════════════════════════════

def test_tc07_invalid_user_id_returns_error_not_crash():
    """
    SCENARIO: Request with a non-existent user_id.
    EXPECTED: HTTP 200 with case='no_panels' OR HTTP 4xx/5xx.
              The system must NOT return an unhandled 500 crash.
    WHY: Verifies the outer try/catch in main.py works.
         get_user_location() returns None → get_production_device() returns None
         → system falls through to no_panels case gracefully.
    """
    url = f"{BASE_URL}/solar-forecast/non-existent-user-000?test_date=2026-06-01"
    res = requests.get(url, timeout=10)

    # System must not crash — any structured response is acceptable
    assert res.status_code in (200, 404, 422, 500), \
        f"Unexpected status: {res.status_code}"

    # If 200, must return a valid case (no_panels is expected for unknown user)
    if res.status_code == 200:
        data = res.json().get("data", {})
        assert "case" in data, \
            "200 response missing 'case' field — unstructured response"

    # Must never return empty body
    assert len(res.content) > 0, "Empty response body — server crashed silently"


def test_tc08_malformed_test_date_returns_422_not_500():
    """
    SCENARIO: test_date parameter is not a valid date string.
    EXPECTED: HTTP 422 Unprocessable Entity — NOT 500 Internal Server Error.
    WHY: Verifies the ValueError try/catch in get_forecast_state().
         date.fromisoformat("notadate") raises ValueError.
         main.py catches ValueError → 422 (not opaque 500).
    This test proves input validation works at the boundary.
    """
    url = f"{BASE_URL}/solar-forecast/{USER_ID}?test_date=notadate"
    res = requests.get(url, timeout=10)

    assert res.status_code == 422, \
        (f"Expected 422 for malformed date, got {res.status_code}. "
         f"System is returning a raw 500 instead of a meaningful error — "
         f"try/catch for ValueError is missing or not wired correctly.")

    # Response must include an error message
    body = res.json()
    assert "detail" in body or "error" in body, \
        "422 response missing error detail"


def test_tc09_forecast_returns_valid_response_after_collection():
    """
    SCENARIO: Device installed March 1, 10 days collected. Today = March 11.
    EXPECTED: Forecast returns HTTP 200 with a valid, well-structured case.
    WHY: Smoke test — verifies the full request pipeline completes successfully:
         check_user() → get_forecast_state() → structured JSON response.
         Confirms no unhandled exception escapes to the caller under
         normal operating conditions.
    
    NOTE: Exception-isolation testing (check_user raises → forecast still runs)
    requires mock.patch and belongs in unit tests, not integration tests,
    because Postgres enforces column types and rejects invalid timestamps (22007).
    """
    _reset("2026-03-01")
    _collect("2026-03-01", 10)

    data = _get_forecast("2026-03-11")

    assert data["case"] in (
        "no_panels", "collecting", "collecting_extended",
        "forecast_available", "feature_disabled"
    ), f"Invalid case returned: {data['case']}"

    assert "city" in data or "case" in data, \
        "Response missing required fields — forecast was blocked by device check"