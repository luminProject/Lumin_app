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
  python -m pytest tests/test_integration_solar.py -v
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
    Clear energycalculation, reset last_reading_at and installation_date.
    sensor_data no longer used.
    """
    device    = _get_device()
    device_id = device["device_id"]
    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
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
    rows = (
        db.table("device").select("device_id")
        .eq("user_id", USER_ID).eq("device_type", "production").execute()
    ).data
    if rows:
        pytest.skip("TC-01 requires no production device.")
    data = _get_forecast("2026-03-01")
    assert data["case"] == "no_panels"
    assert "avg_daily_ghi" in data
    assert data["avg_daily_ghi"] > 0


def test_tc02_collecting_case():
    _reset("2026-03-01")
    _collect("2026-03-01", 10)
    data = _get_forecast("2026-03-11")
    assert data["case"] == "collecting"
    assert data["collected_days"] == 10
    assert data["days_offline"] == 0
    assert data["season"] == "spring"


def test_tc03_collecting_extended_case():
    _reset("2026-02-01")
    _collect("2026-02-01", 10)
    data = _get_forecast("2026-02-11")
    assert data["case"] == "collecting_extended"
    assert data["next_season"] == "spring"
    assert data["days_remaining_from_install"] < 45


def test_tc04_forecast_available_case():
    _reset("2026-03-01")
    _collect("2026-03-01", 92)
    data = _get_forecast("2026-06-01")
    assert data["case"] == "forecast_available"
    assert data["prev_season"] == "spring"
    assert "actual_by_month" in data
    assert len(data["actual_by_month"]) > 0


def test_tc05_feature_disabled_after_15_days_offline():
    _reset("2026-03-01")
    last         = _collect("2026-03-01", 92)
    virtual_date = _offline(last, 15)
    data = _get_forecast(virtual_date.isoformat())
    assert data["case"] == "feature_disabled"
    assert data["days_offline"] >= 15
    assert "last_reading_date" in data


def test_tc05b_device_warning_offline_less_than_15_days():
    _reset("2026-03-01")
    last         = _collect("2026-03-01", 92)
    virtual_date = _offline(last, 5)
    data = _get_forecast(virtual_date.isoformat())
    assert data["case"] == "forecast_available"
    assert data["days_offline"] == 5


def test_tc06_reconnect_resets_offline_state():
    _reset("2026-03-01")
    last         = _collect("2026-03-01", 92)
    virtual_date = _offline(last, 15)
    _reconnect(virtual_date)
    data = _get_forecast(virtual_date.isoformat())
    assert data["case"] == "forecast_available"
    assert data["days_offline"] == 0


def test_tc07_stats_week_returns_7_points():
    data   = _get_stats("week", "2026-05-05")
    points = data["points"]
    assert data["range"] == "week"
    assert len(points) == 7
    assert points[0]["label"] == "Sat"
    assert points[-1]["label"] == "Fri"


def test_tc08_stats_month_returns_4_weekly_buckets():
    data   = _get_stats("month", "2026-05")
    points = data["points"]
    assert data["range"] == "month"
    assert len(points) == 4
    assert [p["label"] for p in points] == ["W1", "W2", "W3", "W4"]


def test_tc09_stats_year_returns_12_monthly_points():
    data   = _get_stats("year", "2026")
    points = data["points"]
    assert data["range"] == "year"
    assert len(points) == 12
    expected = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
    assert [p["label"] for p in points] == expected
    assert points[2]["solar"] > 0