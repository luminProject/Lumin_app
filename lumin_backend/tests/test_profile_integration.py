import os
from datetime import date, timedelta

import pytest

from app.core.lumin_facade import LuminFacade
from app.core.database_manager import DatabaseManager
from app.supabase_client import supabase_admin


TEST_USER_ID = os.getenv("LUMIN_TEST_USER_ID", "9fa36d4f-e57d-4109-b079-ab19273e30ec")


@pytest.fixture(scope="module")
def facade():
    return LuminFacade(supabase_admin)


@pytest.fixture(scope="module")
def db():
    return DatabaseManager(supabase_admin)


def valid_payload():
    return {
        "username": "Shorouq Test",
        "phone_number": "+966512345678",
        "energy_source": "Grid only",
        "has_solar_panels": None,
        "last_billing_end_date": (date.today() - timedelta(days=5)).isoformat(),
    }


def test_get_profile_success(facade):
    result = facade.get_profile(TEST_USER_ID)

    assert result["user_id"] == TEST_USER_ID
    assert "username" in result
    assert "phone_number" in result
    assert "energy_source" in result
    assert "last_billing_end_date" in result


def test_update_profile_valid_data_saved_in_db(facade, db):
    payload = valid_payload()

    result = facade.update_profile(TEST_USER_ID, payload)
    row = db.get_user_profile_row(TEST_USER_ID)

    assert result["username"] == payload["username"]
    assert result["phone_number"] == payload["phone_number"]
    assert result["energy_source"] == "Grid only"
    assert result["has_solar_panels"] is None

    assert row is not None
    assert row["username"] == payload["username"]
    assert row["phone_number"] == payload["phone_number"]

