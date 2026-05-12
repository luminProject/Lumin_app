"""
tests/test_bill_api.py
==================================

API-level Integration tests for the Bill feature.

Integration path:
HTTP Request
→ FastAPI Endpoint
→ Auth/RLS
→ LuminFacade
→ DatabaseManager
→ EnergyCalculation
→ BillPrediction
→ Supabase DB
→ Notification table

What these tests verify:
- POST /bill/{user_id}
- GET  /bill/{user_id}
- POST /internal/run-bill-checkpoint

Verified behaviors:
- Correct HTTP status codes
- Correct JSON structure
- Bill row saved to DB
- Current usage calculated correctly
- Actual bill calculated correctly
- setup_required flow works
- Checkpoint prediction works
- Notification row created when limit exceeded

HOW TO RUN:

1) Start backend:
    cd lumin_backend
    uvicorn app.main:app --reload

2) Run tests:
    python -m pytest tests/test_bill_api.py -v -s

REQUIREMENTS:
- Backend running on http://127.0.0.1:8000
- Test user must exist in Supabase Auth + users table
- .env file must contain:

    SUPABASE_URL=
    SUPABASE_KEY=
    SUPABASE_SERVICE_ROLE_KEY=

    TEST_USER_EMAIL=
    TEST_USER_PASSWORD=
    TEST_USER_ID=
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
import requests
import supabase as sb

from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

BASE_URL = "http://127.0.0.1:8000"

TEST_USER_ID = os.getenv("TEST_USER_ID", "")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "")

pytestmark = pytest.mark.integration


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _get(path: str, token: str | None = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    return requests.get(
        f"{BASE_URL}{path}",
        headers=headers,
        timeout=30,
    )


def _post(
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> requests.Response:

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    return requests.post(
        f"{BASE_URL}{path}",
        json=body or {},
        headers=headers,
        timeout=30,
    )


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def supabase_client():

    if not all([
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
    ]):
        pytest.skip("Missing Supabase credentials.")

    return sb.create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
    )


@pytest.fixture(scope="module")
def auth_token():
    """
    Sign in using a real Supabase user
    and get a real JWT token.
    """

    if not all([
        SUPABASE_URL,
        SUPABASE_KEY,
        TEST_USER_EMAIL,
        TEST_USER_PASSWORD,
    ]):
        pytest.skip("Missing test auth credentials in .env")

    client = sb.create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )

    try:
        response = client.auth.sign_in_with_password({
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        })

        token = response.session.access_token

        assert token, "Failed to get JWT token"

        return token

    except Exception as e:
        pytest.skip(f"Could not login test user: {e}")


@pytest.fixture(scope="module", autouse=True)
def check_backend():
    """
    Skip tests if backend is not running.
    """

    try:
        r = requests.get(f"{BASE_URL}/", timeout=3)

        if r.status_code != 200:
            pytest.skip("Backend is not running.")

    except Exception:
        pytest.skip("Backend is not running.")


@pytest.fixture(autouse=True)
def cleanup(supabase_client):

    yield

    supabase_client.table("billprediction") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    supabase_client.table("energycalculation") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    supabase_client.table("notification") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .in_("notification_type", ["bill_warning", "bill_update"]) \
        .execute()


# ═══════════════════════════════════════════════════════════════
# TEST HELPERS
# ═══════════════════════════════════════════════════════════════

def set_last_billing_end_date(
    supabase_client,
    last_end: date | None,
):

    payload = {
        "last_billing_end_date":
            last_end.isoformat() if last_end else None
    }

    supabase_client.table("users") \
        .update(payload) \
        .eq("user_id", TEST_USER_ID) \
        .execute()


def insert_energy_days(
    supabase_client,
    cycle_start: date,
    days: int,
    consumption: float,
    solar: float = 0.0,
):

    rows = []

    for i in range(days):

        rows.append({
            "user_id": TEST_USER_ID,
            "date": (cycle_start + timedelta(days=i)).isoformat(),
            "total_consumption": consumption,
            "solar_production": solar,
            "total_cost": round(consumption * 0.18, 4),
            "cost_savings": round(solar * 0.18, 4),
            "carbon_reduction": round(solar * 0.568, 6),
        })

    supabase_client.table("energycalculation") \
        .insert(rows) \
        .execute()


def get_bill_row(
    supabase_client,
    cycle_start: date,
):

    rows = (
        supabase_client.table("billprediction")
        .select("*")
        .eq("user_id", TEST_USER_ID)
        .eq("cycle_start", cycle_start.isoformat())
        .limit(1)
        .execute()
    ).data or []

    return rows[0] if rows else None


# ═══════════════════════════════════════════════════════════════
# POST /bill/{user_id}
# ═══════════════════════════════════════════════════════════════

class TestSetBillLimitEndpoint:

    def test_returns_200(
        self,
        auth_token,
        supabase_client,
    ):

        cycle_start = date.today() - timedelta(days=3)

        set_last_billing_end_date(
            supabase_client,
            cycle_start - timedelta(days=1),
        )

        insert_energy_days(
            supabase_client,
            cycle_start,
            days=3,
            consumption=10,
            solar=2,
        )

        r = _post(
            f"/bill/{TEST_USER_ID}",
            body={"limit_amount": 200},
            token=auth_token,
        )

        assert r.status_code == 200


    def test_bill_row_saved_to_database(
        self,
        auth_token,
        supabase_client,
    ):

        cycle_start = date.today() - timedelta(days=3)

        set_last_billing_end_date(
            supabase_client,
            cycle_start - timedelta(days=1),
        )

        insert_energy_days(
            supabase_client,
            cycle_start,
            days=3,
            consumption=10,
            solar=2,
        )

        _post(
            f"/bill/{TEST_USER_ID}",
            body={"limit_amount": 200},
            token=auth_token,
        )

        row = get_bill_row(
            supabase_client,
            cycle_start,
        )

        assert row is not None
        assert float(row["limit_amount"]) == 200
        assert float(row["current_usage_kwh"]) == 24.0
        assert float(row["actual_bill"]) == 4.32


# ═══════════════════════════════════════════════════════════════
# GET /bill/{user_id}
# ═══════════════════════════════════════════════════════════════

class TestGetBillEndpoint:

    def test_returns_200(
        self,
        auth_token,
        supabase_client,
    ):

        cycle_start = date.today() - timedelta(days=4)

        set_last_billing_end_date(
            supabase_client,
            cycle_start - timedelta(days=1),
        )

        insert_energy_days(
            supabase_client,
            cycle_start,
            days=4,
            consumption=12,
            solar=2,
        )

        r = _get(
            f"/bill/{TEST_USER_ID}",
            auth_token,
        )

        assert r.status_code == 200


    def test_response_contains_current_bill_data(
        self,
        auth_token,
        supabase_client,
    ):

        cycle_start = date.today() - timedelta(days=4)

        set_last_billing_end_date(
            supabase_client,
            cycle_start - timedelta(days=1),
        )

        insert_energy_days(
            supabase_client,
            cycle_start,
            days=4,
            consumption=12,
            solar=2,
        )

        r = _get(
            f"/bill/{TEST_USER_ID}",
            auth_token,
        )

        body = r.json()
        data = body["data"]

        assert body["status"] == "success"
        assert data["setup_required"] is False
        assert data["current_usage_kwh"] == 40.0
        assert data["actual_bill"] == 7.2
        assert data["cycle_start"] == cycle_start.isoformat()


    def test_missing_billing_date_returns_setup_required(
        self,
        auth_token,
        supabase_client,
    ):

        set_last_billing_end_date(
            supabase_client,
            None,
        )

        r = _get(
            f"/bill/{TEST_USER_ID}",
            auth_token,
        )

        body = r.json()
        data = body["data"]

        assert r.status_code == 200
        assert data["setup_required"] is True
        assert data["cycle_start"] is None
        assert data["forecast_available"] is False


# ═══════════════════════════════════════════════════════════════
# POST /internal/run-bill-checkpoint
# ═══════════════════════════════════════════════════════════════

class TestBillCheckpointEndpoint:

    def test_checkpoint_prediction_updates_bill_row(
        self,
        supabase_client,
    ):

        cycle_start = date.today() - timedelta(days=8)

        set_last_billing_end_date(
            supabase_client,
            cycle_start - timedelta(days=1),
        )

        insert_energy_days(
            supabase_client,
            cycle_start,
            days=7,
            consumption=20,
            solar=0,
        )

        supabase_client.table("billprediction") \
            .upsert({
                "user_id": TEST_USER_ID,
                "cycle_start": cycle_start.isoformat(),
                "limit_amount": 500,
                "actual_bill": 0,
                "predicted_bill": 0,
                "current_usage_kwh": 0,
                "predicted_usage_kwh": 0,
                "forecast_available": False,
                "last_checkpoint_day": None,
            }, on_conflict="user_id,cycle_start") \
            .execute()

        r = _post("/internal/run-bill-checkpoint")

        assert r.status_code == 200

        row = get_bill_row(
            supabase_client,
            cycle_start,
        )

        assert row is not None
        assert row["forecast_available"] is True
        assert int(row["last_checkpoint_day"]) == 7
        assert float(row["predicted_usage_kwh"]) == 600.0
        assert float(row["predicted_bill"]) == 108.0


    def test_notification_created_when_limit_exceeded(
        self,
        supabase_client,
    ):

        cycle_start = date.today() - timedelta(days=8)

        set_last_billing_end_date(
            supabase_client,
            cycle_start - timedelta(days=1),
        )

        insert_energy_days(
            supabase_client,
            cycle_start,
            days=7,
            consumption=50,
            solar=0,
        )

        supabase_client.table("billprediction") \
            .upsert({
                "user_id": TEST_USER_ID,
                "cycle_start": cycle_start.isoformat(),
                "limit_amount": 100,
                "actual_bill": 0,
                "predicted_bill": 0,
                "current_usage_kwh": 0,
                "predicted_usage_kwh": 0,
                "forecast_available": False,
                "last_checkpoint_day": None,
            }, on_conflict="user_id,cycle_start") \
            .execute()

        r = _post("/internal/run-bill-checkpoint")

        assert r.status_code == 200

        notifications = (
            supabase_client.table("notification")
            .select("notification_type")
            .eq("user_id", TEST_USER_ID)
            .in_("notification_type", ["bill_warning", "bill_update"])
            .execute()
        ).data or []

        assert len(notifications) >= 1
        assert notifications[0]["notification_type"] in {
            "bill_warning",
            "bill_update",
        }