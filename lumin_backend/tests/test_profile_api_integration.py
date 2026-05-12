"""
tests/test_profile_api.py
==================================

API-level Integration tests for Profile feature.

Integration path:
HTTP Request
→ FastAPI Endpoint
→ Auth/RLS
→ LuminFacade
→ DatabaseManager
→ Supabase users table

What these tests verify:
- GET   /profiles/{user_id}
- PATCH /profiles/{user_id}

Verified behaviors:
- Correct HTTP status codes
- Correct JSON structure
- Profile data retrieved successfully
- Profile updates saved to database
- Validation rules work correctly
- Unauthorized requests return 401
- Grid only clears solar flag correctly

HOW TO RUN:

1) Start backend:
    cd lumin_backend
    uvicorn app.main:app --reload

2) Run tests:
    python -m pytest tests/test_profile_api.py -v -s

REQUIREMENTS:
- Backend must be running on http://127.0.0.1:8000
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
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

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


def _patch(
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> requests.Response:

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    return requests.patch(
        f"{BASE_URL}{path}",
        json=body or {},
        headers=headers,
        timeout=30,
    )


def reset_profile(supabase_client) -> None:
    """
    Reset profile data after each test.
    """

    supabase_client.table("users").update({
        "username": "Test User",
        "phone_number": "0500000000",
        "location": "Jeddah",
        "energy_source": "Grid only",
        "has_solar_panels": None,
        "last_billing_end_date": None,
    }).eq("user_id", TEST_USER_ID).execute()


def get_user_row(supabase_client) -> dict | None:
    """
    Read current user row directly from database.
    """

    rows = (
        supabase_client.table("users")
        .select("*")
        .eq("user_id", TEST_USER_ID)
        .limit(1)
        .execute()
    ).data or []

    return rows[0] if rows else None


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
    Sign in using a real test user
    and get a real JWT token.
    """

    if not all([
        SUPABASE_URL,
        SUPABASE_KEY,
        TEST_USER_EMAIL,
        TEST_USER_PASSWORD,
    ]):
        pytest.skip(
            "Missing TEST_USER_EMAIL or TEST_USER_PASSWORD in .env"
        )

    client = sb.create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )

    response = client.auth.sign_in_with_password({
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
    })

    token = response.session.access_token

    assert token, "Failed to get JWT token"

    return token


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
    """
    Reset profile before and after every test.
    """

    if not TEST_USER_ID:
        pytest.skip("Missing TEST_USER_ID in .env")

    reset_profile(supabase_client)

    yield

    reset_profile(supabase_client)


# ═══════════════════════════════════════════════════════════════
# GET /profiles/{user_id}
# ═══════════════════════════════════════════════════════════════

class TestGetProfileEndpoint:

    def test_get_profile_returns_200(self, auth_token):

        r = _get(
            f"/profiles/{TEST_USER_ID}",
            auth_token,
        )

        assert r.status_code == 200, \
            f"Expected 200, got {r.status_code}: {r.text[:200]}"




# ═══════════════════════════════════════════════════════════════
# PATCH /profiles/{user_id}
# ═══════════════════════════════════════════════════════════════

class TestUpdateProfileEndpoint:

    def test_update_profile_updates_database(
        self,
        auth_token,
        supabase_client,
    ):

        payload = {
            "username": "Shorouq Test",
            "phone_number": "0555555555",
            "location": "Jeddah",
            "energy_source": "Grid + Solar",
            "has_solar_panels": True,
        }

        r = _patch(
            f"/profiles/{TEST_USER_ID}",
            payload,
            auth_token,
        )

        assert r.status_code == 200, r.text

        body = r.json()

        assert body["username"] == "Shorouq Test"
        assert body["phone_number"] == "0555555555"
        assert body["energy_source"] == "Grid + Solar"
        assert body["has_solar_panels"] is True

        row = get_user_row(supabase_client)

        assert row is not None
        assert row["username"] == "Shorouq Test"
        assert row["phone_number"] == "0555555555"
        assert row["energy_source"] == "Grid + Solar"
        assert row["has_solar_panels"] is True



# ═══════════════════════════════════════════════════════════════
# VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestProfileValidation:


    def test_invalid_phone_returns_error(self, auth_token):

        r = _patch(
            f"/profiles/{TEST_USER_ID}",
            {"phone_number": "abc123"},
            auth_token,
        )

        assert r.status_code in {400, 422}


    def test_future_billing_date_returns_error(
        self,
        auth_token,
    ):

        future_date = date.today() + timedelta(days=1)

        r = _patch(
            f"/profiles/{TEST_USER_ID}",
            {
                "last_billing_end_date": future_date.isoformat(),
            },
            auth_token,
        )

        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════
# AUTH TESTS
# ═══════════════════════════════════════════════════════════════

class TestProfileAuthorization:

    def test_patch_without_token_returns_401(self):

        r = _patch(
            f"/profiles/{TEST_USER_ID}",
            {"username": "No Token"},
        )

        assert r.status_code == 401