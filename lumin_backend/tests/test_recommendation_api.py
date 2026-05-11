"""
tests/test_recommendation_api.py
==================================
API-level Integration tests for Recommendations and Notifications.

Integration level:
  HTTP Client → FastAPI Endpoint → LuminFacade → DatabaseManager → Supabase DB

This is a DIFFERENT level from test_recommendation_integration.py:
  - test_recommendation_integration.py → tests Python modules directly
  - test_recommendation_api.py         → tests the actual HTTP endpoints

What these tests verify:
  - GET  /recommendations/{user_id}                        → returns 200 + list
  - GET  /recommendations/all/{user_id}                    → returns 200 + list
  - GET  /recommendations/latest/{user_id}                 → returns 200 or empty
  - POST /recommendations/generate/{user_id}               → returns 200 + saves to DB
  - GET  /recommendations/notifications/{user_id}          → returns 200 + list
  - GET  /recommendations/notifications/latest/{user_id}   → returns 200 or empty
  - All endpoints return correct HTTP status codes
  - All responses have the correct JSON structure

HOW TO RUN:
  1. Start the backend first:
       cd lumin_backend
       uvicorn app.main:app --reload

  2. Run the tests:
       python -m pytest tests/test_recommendation_api.py -v

REQUIREMENTS:
  - Backend must be running on http://127.0.0.1:8000
  - TEST_USER_ID must exist in the Supabase users table
  - general_recommendations table must have at least one row
  - .env file with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (for cleanup)
"""

import os
from datetime import datetime

import pytest
import requests
import supabase as sb
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────

BASE_URL     = "http://127.0.0.1:8000"
TEST_USER_ID = "33b11b04-55ee-4210-917b-9a5b86dc21c0"

SUPABASE_URL              = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Test user credentials — used to get a real JWT token
# Add these to your .env file:
#   TEST_USER_EMAIL=your_test_user@email.com
#   TEST_USER_PASSWORD=your_test_password
TEST_USER_EMAIL    = os.getenv("TEST_USER_EMAIL", "")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "")


# ─── Helpers ─────────────────────────────────────────────────────

def _get(path: str, token: str = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE_URL}{path}", headers=headers, timeout=30)

def _post(path: str, body: dict = None, token: str = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{BASE_URL}{path}", json=body or {}, headers=headers, timeout=30)


# ─── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def supabase_client():
    if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
        pytest.skip("Missing Supabase credentials — cannot run cleanup.")
    return sb.create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


@pytest.fixture(scope="module")
def auth_token():
    """
    Get a real JWT token by signing in with test user credentials.
    Add TEST_USER_EMAIL and TEST_USER_PASSWORD to your .env file.
    """
    if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
        pytest.skip(
            "Missing TEST_USER_EMAIL or TEST_USER_PASSWORD in .env — "
            "cannot get auth token for API tests."
        )
    client = sb.create_client(SUPABASE_URL, os.getenv("SUPABASE_KEY", SUPABASE_SERVICE_ROLE_KEY))
    try:
        response = client.auth.sign_in_with_password({
            "email":    TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        })
        token = response.session.access_token
        assert token, "Failed to get access token from Supabase"
        return token
    except Exception as e:
        pytest.skip(f"Could not sign in to get JWT token: {e}")


@pytest.fixture(autouse=True)
def cleanup(supabase_client):
    """Clean up after every test."""
    yield
    supabase_client.table("recommendation") \
        .delete().eq("user_id", TEST_USER_ID).execute()
    supabase_client.table("notification") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .eq("notification_type", "recommendation") \
        .execute()


@pytest.fixture(scope="module", autouse=True)
def check_backend():
    """Skip all tests if backend is not running."""
    try:
        r = requests.get(f"{BASE_URL}/", timeout=3)
        if r.status_code != 200:
            pytest.skip("Backend is not running on http://127.0.0.1:8000")
    except Exception:
        pytest.skip("Backend is not running on http://127.0.0.1:8000")


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: GET /recommendations/{user_id}
#
#  WHAT WE TEST:
#    The old-style recommendations endpoint returns 200
#    and the correct JSON structure.
#
#  WHY THIS MATTERS:
#    This is the endpoint the Flutter app calls to display
#    the recommendation list. Wrong status or missing fields
#    = Flutter crash.
# ══════════════════════════════════════════════════════════════════

class TestGetRecommendationsEndpoint:

    def test_returns_200(self, auth_token):
        r = _get(f"/recommendations/{TEST_USER_ID}", auth_token)
        assert r.status_code == 200, \
            f"Expected 200, got {r.status_code}: {r.text[:100]}"

    def test_response_is_json(self, auth_token):
        r = _get(f"/recommendations/{TEST_USER_ID}", auth_token)
        assert r.headers["content-type"].startswith("application/json")

    def test_response_has_status_field(self, auth_token):
        r = _get(f"/recommendations/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert "status" in body, f"Missing 'status' in response: {body}"

    def test_data_field_is_a_list(self, auth_token):
        r = _get(f"/recommendations/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert isinstance(body.get("data"), list), \
            f"Expected 'data' to be a list, got: {type(body.get('data'))}"

    def test_invalid_user_returns_200_with_empty_list(self, auth_token):
        r = _get("/recommendations/00000000-0000-0000-0000-000000000099", auth_token)
        assert r.status_code == 200
        body = r.json()
        assert body.get("data") == []


class TestGenerateRecommendationEndpoint:

    def test_returns_200(self, auth_token):
        r = _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        assert r.status_code == 200, \
            f"Expected 200, got {r.status_code}: {r.text[:200]}"

    def test_response_success_is_true(self, auth_token):
        r = _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        body = r.json()
        assert body.get("success") is True, \
            f"Expected success=True, got: {body}"

    def test_response_has_recommendation_field(self, auth_token):
        r = _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        body = r.json()
        assert body.get("recommendation") is not None, \
            "Response missing 'recommendation' field"

    def test_recommendation_text_is_not_empty(self, auth_token):
        r = _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        body = r.json()
        rec = body.get("recommendation", {})
        text = rec.get("recommendation_text", "") if isinstance(rec, dict) else ""
        assert len(text) > 5, f"Recommendation text too short: '{text}'"

    def test_recommendation_appears_in_get_all(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/all/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert len(body.get("data", [])) >= 1, \
            "Recommendation not found in GET /all/ after generate"

    def test_two_calls_create_two_rows(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/all/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert len(body.get("data", [])) >= 2


class TestGetAllRecommendationsEndpoint:

    def test_returns_200(self, auth_token):
        r = _get(f"/recommendations/all/{TEST_USER_ID}", auth_token)
        assert r.status_code == 200

    def test_data_is_list(self, auth_token):
        r = _get(f"/recommendations/all/{TEST_USER_ID}", auth_token)
        assert isinstance(r.json().get("data"), list)

    def test_empty_when_no_recommendations(self, auth_token):
        r = _get(f"/recommendations/all/{TEST_USER_ID}", auth_token)
        assert r.json().get("data") == []

    def test_contains_recommendation_after_generate(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/all/{TEST_USER_ID}", auth_token)
        assert len(r.json().get("data", [])) >= 1


class TestGetLatestRecommendationEndpoint:

    def test_returns_200(self, auth_token):
        r = _get(f"/recommendations/latest/{TEST_USER_ID}", auth_token)
        assert r.status_code == 200

    def test_empty_when_no_recommendations(self, auth_token):
        r = _get(f"/recommendations/latest/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert body.get("success") is False or body.get("data") is None

    def test_returns_data_after_generate(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/latest/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert body.get("success") is True
        assert body.get("data") is not None

    def test_data_has_recommendation_text(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/latest/{TEST_USER_ID}", auth_token)
        data = r.json().get("data", {})
        assert "recommendation_text" in data, \
            f"Missing 'recommendation_text' in: {data}"


class TestGetNotificationsEndpoint:

    def test_returns_200(self, auth_token):
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        assert r.status_code == 200

    def test_data_is_list(self, auth_token):
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        assert isinstance(r.json().get("data"), list)

    def test_empty_when_no_notifications(self, auth_token):
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        assert r.json().get("data") == []

    def test_notification_appears_after_generate(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        data = r.json().get("data", [])
        assert len(data) >= 1, "No notification found after generate"

    def test_notification_type_is_recommendation(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        types = [n.get("notification_type") for n in r.json().get("data", [])]
        assert "recommendation" in types

    def test_notification_has_required_fields(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        notif = r.json().get("data", [{}])[0]
        for field in ["user_id", "notification_type", "content", "timestamp"]:
            assert field in notif, f"Missing field '{field}'"

    def test_notifications_ordered_newest_first(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        timestamps = [
            datetime.fromisoformat(str(n["timestamp"]).replace("Z", "+00:00"))
            for n in r.json().get("data", [])
            if n.get("timestamp")
        ]
        assert timestamps == sorted(timestamps, reverse=True), \
            "Notifications not ordered newest-first"


class TestGetLatestNotificationEndpoint:

    def test_returns_200(self, auth_token):
        r = _get(f"/recommendations/notifications/latest/{TEST_USER_ID}", auth_token)
        assert r.status_code == 200

    def test_empty_when_no_notifications(self, auth_token):
        r = _get(f"/recommendations/notifications/latest/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert body.get("success") is False or body.get("data") is None

    def test_returns_data_after_generate(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/notifications/latest/{TEST_USER_ID}", auth_token)
        body = r.json()
        assert body.get("success") is True
        assert body.get("data") is not None

    def test_data_has_required_fields(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        r = _get(f"/recommendations/notifications/latest/{TEST_USER_ID}", auth_token)
        data = r.json().get("data", {})
        for field in ["user_id", "notification_type", "content", "timestamp"]:
            assert field in data, f"Missing field '{field}' in: {data}"

    def test_latest_matches_first_in_all_list(self, auth_token):
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)
        _post(f"/recommendations/generate/{TEST_USER_ID}", token=auth_token)

        all_r    = _get(f"/recommendations/notifications/{TEST_USER_ID}", auth_token)
        latest_r = _get(f"/recommendations/notifications/latest/{TEST_USER_ID}", auth_token)

        all_notifs = all_r.json().get("data", [])
        latest     = latest_r.json().get("data", {})

        if all_notifs and latest:
            assert all_notifs[0].get("content") == latest.get("content"), \
                "Latest notification doesn't match first item in all list"