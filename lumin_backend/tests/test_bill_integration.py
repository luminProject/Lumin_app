"""
Integration level:
LuminFacade <-> DatabaseManager <-> EnergyCalculation <-> BillPrediction

Methods under test:
1. get_my_current_bill()
2. set_bill_limit()
3. run_bill_checkpoint_for_user()
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import supabase as sb
from dotenv import load_dotenv

from app.core.lumin_facade import LuminFacade
from app.core.database_manager import DatabaseManager
from app.models.bill_prediction import BillPrediction
from app.models.energy_calculation import EnergyCalculation

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

TEST_USER_ID = "9fa36d4f-e57d-4109-b079-ab19273e30ec"
TODAY = datetime.now(ZoneInfo("Asia/Riyadh")).date()

pytestmark = pytest.mark.skipif(
    not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]),
    reason="Missing Supabase credentials in .env",
)


@pytest.fixture(scope="module")
def supabase_client():
    return sb.create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
    )


@pytest.fixture(scope="module")
def facade(supabase_client):
    return LuminFacade(supabase_client)


@pytest.fixture(scope="module")
def db(supabase_client):
    return DatabaseManager(supabase_client)


@pytest.fixture(scope="module")
def cycle_start(db):
    last_end = db.get_user_last_billing_end_date(TEST_USER_ID)

    if not last_end:
        pytest.skip(
            "TEST_USER_ID has no last_billing_end_date. "
            "Set it in Supabase before running."
        )

    current_cycle_start = last_end + timedelta(days=1)

    while TODAY > current_cycle_start + timedelta(days=29):
        current_cycle_start += timedelta(days=30)

    return current_cycle_start


def prepare_bill_test_data(db, cycle_start):
    previous_bill_end = cycle_start - timedelta(days=1)
    cycle_end = cycle_start + timedelta(days=29)

    db.supabase.table("users").update({
        "last_billing_end_date": previous_bill_end.isoformat(),
    }).eq("user_id", TEST_USER_ID).execute()

    db.supabase.table("energycalculation").delete() \
        .eq("user_id", TEST_USER_ID) \
        .gte("date", cycle_start.isoformat()) \
        .lte("date", cycle_end.isoformat()) \
        .execute()

    db.supabase.table("billprediction").delete() \
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


def test_actual_bill_matches_tariff(facade, db, cycle_start):
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


def test_valid_limit_saved_in_db(facade, db, cycle_start):
    facade.set_bill_limit(TEST_USER_ID, 500)

    row = db.get_bill_row_by_cycle(TEST_USER_ID, cycle_start)

    assert row is not None, "No bill row found after set_bill_limit."
    assert float(row["limit_amount"]) == pytest.approx(500.0, abs=0.01)


def test_checkpoint_saves_prediction_with_prepared_data(facade, db):
    cycle_start = TODAY - timedelta(days=7)

    prepare_bill_test_data(db, cycle_start)

    facade.run_bill_checkpoint_for_user(TEST_USER_ID)

    row = db.get_bill_row_by_cycle(TEST_USER_ID, cycle_start)

    assert row is not None, "No bill row found after checkpoint."
    assert row.get("forecast_available") is True
    assert row.get("last_checkpoint_day") == 7
    assert float(row.get("predicted_usage_kwh") or 0) == pytest.approx(300.0, abs=0.01)
    assert float(row.get("predicted_bill") or 0) == pytest.approx(54.0, abs=0.01)