"""
tests/test_profile_integration.py
========================================
Integration tests for the Profile feature.

Integration level:
  LuminFacade <-> DatabaseManager <-> Supabase DB

Methods under test:
  1. get_profile(user_id)
  2. update_profile(user_id, payload)

What these tests verify:
  - get_profile() returns the required profile fields
  - update_profile() saves valid profile data in Supabase
  - Billing date changes are persisted because the Bill feature depends on it
  - Solar-related profile fields are saved correctly
  - Updates belong to the correct user only

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_profile_integration.py -v

REQUIREMENTS:
  - .env file with Supabase credentials configured by app.supabase_client
  - LUMIN_TEST_USER_ID must exist in the users table, or the default test user must exist
"""

import os
from datetime import date, timedelta

import pytest

from app.core.database_manager import DatabaseManager
from app.core.lumin_facade import LuminFacade
from app.supabase_client import supabase_admin

TEST_USER_ID = os.getenv(
    "LUMIN_TEST_USER_ID",
    "9fa36d4f-e57d-4109-b079-ab19273e30ec",
)


# ─── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def facade():
    return LuminFacade(supabase_admin)


@pytest.fixture(scope="module")
def db():
    return DatabaseManager(supabase_admin)


@pytest.fixture(scope="module")
def test_user_exists(db):
    row = db.get_user_profile_row(TEST_USER_ID)
    if not row:
        pytest.skip(f"Test user {TEST_USER_ID} was not found in the users table.")
    return TEST_USER_ID


@pytest.fixture(autouse=True)
def cleanup_profile(db):
    """
    Restore the original profile after every test.

    Profile tests update a real Supabase row. This fixture prevents one test
    from leaking data into the next test or permanently changing the test user.
    """
    original = db.get_user_profile_row(TEST_USER_ID)

    yield

    if original:
        restore_payload = {
            "username": original.get("username"),
            "phone_number": original.get("phone_number"),
            "energy_source": original.get("energy_source"),
            "has_solar_panels": original.get("has_solar_panels"),
            "last_billing_end_date": original.get("last_billing_end_date"),
        }

        db.supabase.table("users") \
            .update(restore_payload) \
            .eq("user_id", TEST_USER_ID) \
            .execute()


# ─── Helpers ─────────────────────────────────────────────────────

def _valid_grid_payload():
    return {
        "username": "Shorouq Test",
        "phone_number": "+966512345678",
        "energy_source": "Grid only",
        "has_solar_panels": None,
        "last_billing_end_date": (date.today() - timedelta(days=5)).isoformat(),
    }


def _valid_solar_payload():
    return {
        "username": "Shorouq Solar Test",
        "phone_number": "+966500000000",
        "energy_source": "Grid + Solar",
        "has_solar_panels": True,
        "last_billing_end_date": (date.today() - timedelta(days=10)).isoformat(),
    }


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: get_profile
#
#  WHAT WE TEST:
#    get_profile() must return a readable profile object with the fields
#    used by the Flutter Profile page and Bill setup flow.
#
#  WHY THIS MATTERS:
#    The app reads these keys directly. Missing user_id, energy source,
#    phone number, or last_billing_end_date can break Profile display or
#    prevent the Bill feature from calculating the billing cycle.
# ══════════════════════════════════════════════════════════════════

class TestGetProfile:


    def test_get_profile_returns_required_fields(self, facade, test_user_exists):
        result = facade.get_profile(TEST_USER_ID)

        required_fields = [
            "user_id",
            "username",
            "phone_number",
            "energy_source",
            "has_solar_panels",
            "last_billing_end_date",
        ]

        for field in required_fields:
            assert field in result, f"Missing profile field: {field}"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: update_profile — Grid-only profile
#
#  WHAT WE TEST:
#    update_profile() must save valid grid-only profile data in Supabase.
#
#  WHY THIS MATTERS:
#    Grid-only users should not be forced to have solar-panel data. The DB
#    row must reflect that has_solar_panels can be None for this case.
# ══════════════════════════════════════════════════════════════════

class TestUpdateGridOnlyProfile:

    def test_update_profile_valid_grid_data_saved_in_db(self, facade, db, test_user_exists):
        payload = _valid_grid_payload()

        result = facade.update_profile(TEST_USER_ID, payload)
        row = db.get_user_profile_row(TEST_USER_ID)

        assert row is not None
        assert result["username"] == payload["username"]
        assert result["phone_number"] == payload["phone_number"]
        assert result["energy_source"] == "Grid only"
        assert result["has_solar_panels"] is None

        assert row["username"] == payload["username"]
        assert row["phone_number"] == payload["phone_number"]
        assert row["energy_source"] == "Grid only"
        assert row["has_solar_panels"] is None
        assert str(row["last_billing_end_date"])[:10] == payload["last_billing_end_date"]
# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: update_profile — Solar profile
#
#  WHAT WE TEST:
#    update_profile() must save solar-related fields correctly when the
#    user profile indicates solar + grid energy source.
#
#  WHY THIS MATTERS:
#    Other features depend on the profile energy source to decide whether
#    solar-related screens, statistics, and forecast behavior should apply.
# ══════════════════════════════════════════════════════════════════

class TestUpdateSolarProfile:

    def test_update_profile_valid_solar_data_saved_in_db(self, facade, db, test_user_exists):
        payload = _valid_solar_payload()

        result = facade.update_profile(TEST_USER_ID, payload)
        row = db.get_user_profile_row(TEST_USER_ID)

        assert row is not None
        assert result["username"] == payload["username"]
        assert result["energy_source"] == "Grid + Solar"
        assert result["has_solar_panels"] is True

        assert row["username"] == payload["username"]
        assert row["energy_source"] == "Grid + Solar"
        assert row["has_solar_panels"] is True
        assert row["user_id"] == TEST_USER_ID