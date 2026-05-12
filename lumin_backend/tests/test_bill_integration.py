"""
tests/test_bill_integration.py
========================================
Integration tests for the Bill Prediction feature.

Integration level:
  LuminFacade <-> DatabaseManager <-> EnergyCalculation
               <-> BillPrediction <-> Supabase DB

Methods under test:
  1. get_my_current_bill(user_id)
  2. set_bill_limit(user_id, limit_amount)
  3. run_bill_checkpoint_for_user(user_id)

What these tests verify:
  - The current bill returned by the Facade matches the tariff logic
  - set_bill_limit() creates or updates a billprediction row in Supabase
  - Bill rows belong to the correct user and current billing cycle
  - A checkpoint run reads real energycalculation rows and saves prediction data
  - Forecast fields are stored correctly after a valid day-7 checkpoint
  - The same checkpoint is not duplicated when the job runs again

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_bill_integration.py -v -s

REQUIREMENTS:
  - .env file with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
  - TEST_USER_ID must exist in the users table in Supabase
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import supabase as sb
from dotenv import load_dotenv

from app.core.database_manager import DatabaseManager
from app.core.lumin_facade import LuminFacade
from app.models.bill_prediction import BillPrediction
from app.models.energy_calculation import EnergyCalculation

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TEST_USER_ID = os.getenv(
    "LUMIN_TEST_USER_ID",
    "9fa36d4f-e57d-4109-b079-ab19273e30ec",
)

TODAY = datetime.now(ZoneInfo("Asia/Riyadh")).date()

pytestmark = pytest.mark.skipif(
    not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]),
    reason="Missing Supabase credentials in .env — skipping bill integration tests.",
)


# ─── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def supabase_client():
    """Real Supabase client using the service role key."""
    return sb.create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


@pytest.fixture(scope="module")
def facade(supabase_client):
    return LuminFacade(supabase_client)


@pytest.fixture(scope="module")
def db(supabase_client):
    return DatabaseManager(supabase_client)


@pytest.fixture(scope="module")
def test_user_exists(db):
    row = db.get_user_profile_row(TEST_USER_ID)
    if not row:
        pytest.skip(f"Test user {TEST_USER_ID} was not found in the users table.")
    return TEST_USER_ID


def _prepare_test_user_billing_setup(db):
    """
    Ensure the integration test user has a valid billing setup.

    This prevents tests from being skipped just because last_billing_end_date
    is missing in the real Supabase users table.
    """
    last_billing_end_date = TODAY - timedelta(days=1)

    db.supabase.table("users") \
        .update({"last_billing_end_date": last_billing_end_date.isoformat()}) \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    return last_billing_end_date


@pytest.fixture(scope="module")
def cycle_start(db, test_user_exists):
    """
    Resolve the active 30-day billing cycle from the user's last bill end date.
    If the test user has no billing date, prepare one automatically.
    """
    last_end = db.get_user_last_billing_end_date(TEST_USER_ID)

    if not last_end:
        last_end = _prepare_test_user_billing_setup(db)

    current_cycle_start = last_end + timedelta(days=1)

    while TODAY > current_cycle_start + timedelta(days=29):
        current_cycle_start += timedelta(days=30)

    return current_cycle_start


@pytest.fixture(autouse=True)
def cleanup_bill_rows(db):
    """
    Keep the database predictable between tests.

    The tests create billprediction rows and checkpoint energycalculation rows.
    Cleanup removes only rows for the test user and restores the original
    last_billing_end_date after each test.
    """
    original_profile = db.get_user_profile_row(TEST_USER_ID)
    original_last_end = None

    if original_profile:
        original_last_end = original_profile.get("last_billing_end_date")

    yield

    db.supabase.table("billprediction") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    db.supabase.table("energycalculation") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .gte("date", (TODAY - timedelta(days=10)).isoformat()) \
        .lte("date", TODAY.isoformat()) \
        .execute()

    if original_profile:
        db.supabase.table("users") \
            .update({"last_billing_end_date": original_last_end}) \
            .eq("user_id", TEST_USER_ID) \
            .execute()


# ─── Helpers ─────────────────────────────────────────────────────

def _prepare_day_7_checkpoint_data(db, cycle_start):
    """
    Create exactly 7 complete daily rows for the current billing cycle.

    Each day has 10 kWh grid usage. SMA-7 should therefore predict:
      current usage = 70 kWh
      remaining usage = 23 days * 10 kWh
      predicted usage = 300 kWh
      predicted bill = 54 SAR at 0.18 SAR/kWh
    """
    previous_bill_end = cycle_start - timedelta(days=1)
    cycle_end = cycle_start + timedelta(days=29)

    db.supabase.table("users") \
        .update({"last_billing_end_date": previous_bill_end.isoformat()}) \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    db.supabase.table("energycalculation") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .gte("date", cycle_start.isoformat()) \
        .lte("date", cycle_end.isoformat()) \
        .execute()

    db.supabase.table("billprediction") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .eq("cycle_start", cycle_start.isoformat()) \
        .execute()

    rows = []
    for i in range(7):
        day = cycle_start + timedelta(days=i)
        rows.append({
            "user_id": TEST_USER_ID,
            "date": day.isoformat(),
            "total_consumption": 10,
            "solar_production": 0,
            "total_cost": 1.8,
            "cost_savings": 0,
            "carbon_reduction": 0,
        })

    db.supabase.table("energycalculation").insert(rows).execute()


def _prepare_incomplete_checkpoint_data(db, cycle_start, days=6):
    """
    Create fewer than 7 complete daily rows for the current billing cycle.

    This simulates a checkpoint day where the system does not yet have enough
    daily data to produce a reliable SMA-7 prediction.
    """
    previous_bill_end = cycle_start - timedelta(days=1)
    cycle_end = cycle_start + timedelta(days=29)

    db.supabase.table("users") \
        .update({"last_billing_end_date": previous_bill_end.isoformat()}) \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    db.supabase.table("energycalculation") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .gte("date", cycle_start.isoformat()) \
        .lte("date", cycle_end.isoformat()) \
        .execute()

    db.supabase.table("billprediction") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .eq("cycle_start", cycle_start.isoformat()) \
        .execute()

    rows = []
    for i in range(days):
        day = cycle_start + timedelta(days=i)
        rows.append({
            "user_id": TEST_USER_ID,
            "date": day.isoformat(),
            "total_consumption": 10,
            "solar_production": 0,
            "total_cost": 1.8,
            "cost_savings": 0,
            "carbon_reduction": 0,
        })

    db.supabase.table("energycalculation").insert(rows).execute()


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: get_my_current_bill
# ══════════════════════════════════════════════════════════════════

class TestGetCurrentBill:

    def test_actual_bill_matches_tariff(self, facade, db, cycle_start):
        cycle_end = cycle_start + timedelta(days=29)

        rows = db.get_current_cycle_energy_rows(
            TEST_USER_ID,
            cycle_start,
            cycle_end,
        )

        energy = EnergyCalculation(TEST_USER_ID)
        usage_data = energy.get_cycle_usage_summary(rows)

        expected_bill = BillPrediction(TEST_USER_ID).calculateBill(
            usage_data["current_usage_kwh"]
        )

        result = facade.get_my_current_bill(TEST_USER_ID)

        assert result["actual_bill"] == pytest.approx(expected_bill, abs=0.01)

    def test_response_contains_required_bill_fields(self, facade, test_user_exists):
        result = facade.get_my_current_bill(TEST_USER_ID)

        for key in [
            "actual_bill",
            "current_usage_kwh",
            "forecast_available",
            "limit_amount",
        ]:
            assert key in result, f"Missing bill response key: {key}"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: set_bill_limit
# ══════════════════════════════════════════════════════════════════

class TestSetBillLimit:

    def test_valid_limit_saved_in_db(self, facade, db, cycle_start):
        facade.set_bill_limit(TEST_USER_ID, 500)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, cycle_start)

        assert row is not None, "No bill row found after set_bill_limit()."
        assert float(row["limit_amount"]) == pytest.approx(500.0, abs=0.01)

    def test_bill_row_belongs_to_correct_user(self, facade, db, cycle_start):
        facade.set_bill_limit(TEST_USER_ID, 500)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, cycle_start)

        assert row is not None, "No bill row found after set_bill_limit()."
        assert row["user_id"] == TEST_USER_ID

    def test_bill_row_uses_current_cycle_start(self, facade, db, cycle_start):
        facade.set_bill_limit(TEST_USER_ID, 500)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, cycle_start)

        assert row is not None, "No bill row found after set_bill_limit()."
        assert str(row["cycle_start"])[:10] == cycle_start.isoformat()


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: run_bill_checkpoint_for_user
# ══════════════════════════════════════════════════════════════════

class TestRunBillCheckpoint:

    def test_checkpoint_saves_prediction_with_prepared_data(self, facade, db):
        checkpoint_cycle_start = TODAY - timedelta(days=7)
        _prepare_day_7_checkpoint_data(db, checkpoint_cycle_start)

        facade.run_bill_checkpoint_for_user(TEST_USER_ID)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, checkpoint_cycle_start)

        assert row is not None, "No bill row found after checkpoint."
        assert row.get("forecast_available") is True
        assert row.get("last_checkpoint_day") == 7
        assert float(row.get("predicted_usage_kwh")) == pytest.approx(300.0, abs=0.01)
        assert float(row.get("predicted_bill")) == pytest.approx(54.0, abs=0.01)

    def test_checkpoint_prediction_row_belongs_to_correct_user(self, facade, db):
        checkpoint_cycle_start = TODAY - timedelta(days=7)
        _prepare_day_7_checkpoint_data(db, checkpoint_cycle_start)

        facade.run_bill_checkpoint_for_user(TEST_USER_ID)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, checkpoint_cycle_start)

        assert row is not None, "No bill row found after checkpoint."
        assert row["user_id"] == TEST_USER_ID

    def test_checkpoint_is_not_duplicated_when_run_twice(self, facade, db):
        checkpoint_cycle_start = TODAY - timedelta(days=7)
        _prepare_day_7_checkpoint_data(db, checkpoint_cycle_start)

        facade.run_bill_checkpoint_for_user(TEST_USER_ID)
        first_row = db.get_bill_row_by_cycle(TEST_USER_ID, checkpoint_cycle_start)

        facade.run_bill_checkpoint_for_user(TEST_USER_ID)
        second_row = db.get_bill_row_by_cycle(TEST_USER_ID, checkpoint_cycle_start)

        assert first_row is not None
        assert second_row is not None
        assert first_row["limit_id"] == second_row["limit_id"]
        assert second_row["last_checkpoint_day"] == 7


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 4: Failure / Edge Cases
# ══════════════════════════════════════════════════════════════════

class TestBillFailureCases:

    def test_get_current_bill_fails_safely_when_billing_date_is_missing(self, facade, db, test_user_exists):
        """
        If last_billing_end_date is missing, the system cannot calculate the
        30-day billing cycle. It must not return a normal bill response.
        """
        db.supabase.table("users") \
            .update({"last_billing_end_date": None}) \
            .eq("user_id", TEST_USER_ID) \
            .execute()

        try:
            result = facade.get_my_current_bill(TEST_USER_ID)
        except Exception as exc:
            message = str(exc).lower()
            assert (
                "billing" in message
                or "last_billing_end_date" in message
                or "setup" in message
            ), f"Unexpected exception for missing billing date: {exc}"
            return

        assert result.get("setup_required") is True, \
            f"Expected setup_required=True when billing date is missing, got: {result}"

    def test_checkpoint_does_not_create_forecast_when_less_than_7_records(self, facade, db):
        """
        Even if the checkpoint job runs, fewer than 7 completed daily rows
        must not produce a forecast. This prevents misleading predictions.
        """
        checkpoint_cycle_start = TODAY - timedelta(days=7)
        _prepare_incomplete_checkpoint_data(db, checkpoint_cycle_start, days=6)

        facade.set_bill_limit(TEST_USER_ID, 500)

        facade.run_bill_checkpoint_for_user(TEST_USER_ID)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, checkpoint_cycle_start)

        assert row is not None, "Expected bill row to exist after setting limit."
        assert row.get("forecast_available") is False
        assert row.get("last_checkpoint_day") in (None, 0)
        assert row.get("predicted_usage_kwh") in (None, 0, 0.0)
        assert row.get("predicted_bill") in (None, 0, 0.0)

    def test_checkpoint_creates_warning_notification_when_prediction_exceeds_limit(self, facade, db):
        """
        A valid day-7 checkpoint with predicted_bill above limit_amount must
        save the prediction and create a warning notification for the same user.
        """
        checkpoint_cycle_start = TODAY - timedelta(days=7)
        _prepare_day_7_checkpoint_data(db, checkpoint_cycle_start)

        facade.set_bill_limit(TEST_USER_ID, 10)

        facade.run_bill_checkpoint_for_user(TEST_USER_ID)

        row = db.get_bill_row_by_cycle(TEST_USER_ID, checkpoint_cycle_start)

        assert row is not None, "No bill row found after checkpoint."
        assert row.get("forecast_available") is True
        assert float(row.get("predicted_bill")) > float(row.get("limit_amount"))

        notifications = (
            db.supabase.table("notification")
            .select("*")
            .eq("user_id", TEST_USER_ID)
            .order("timestamp", desc=True)
            .limit(5)
            .execute()
            .data
        )

        assert notifications, "Expected a warning notification when predicted bill exceeds limit."

        warning_notifications = [
            n for n in notifications
            if "bill" in str(n.get("notification_type", "")).lower()
            or "limit" in str(n.get("content", "")).lower()
            or "budget" in str(n.get("content", "")).lower()
            or "exceed" in str(n.get("content", "")).lower()
        ]

        assert warning_notifications, \
            f"No bill warning notification found. Latest notifications: {notifications}"