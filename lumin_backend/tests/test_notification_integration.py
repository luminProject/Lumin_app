"""
tests/test_notification_integration.py
========================================
Integration tests for the Notifications feature.

Integration level:
  LuminFacade <-> DatabaseManager <-> Supabase DB

Methods under test:
  1. getNotifications(user_id)     — fetch all notifications
  2. getLatestNotification(user_id) — fetch the most recent one
  3. _send_notification_and_push() — called indirectly via viewRecommendations()

What these tests verify:
  - After a recommendation is generated, getNotifications() includes it
  - getLatestNotification() returns the most recently created notification
  - getNotifications() returns correct structure (success, code, data)
  - getLatestNotification() on empty user returns correct empty response
  - Notifications belong to the correct user only
  - Notifications are ordered newest-first

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_notification_integration.py -v

REQUIREMENTS:
  - .env file with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
  - TEST_USER_ID must exist in the users table in Supabase
  - general_recommendations table must have at least one row
"""

import os
from datetime import datetime, timezone

import pytest
import supabase as sb
from dotenv import load_dotenv

from app.core.lumin_facade import LuminFacade
from app.core.database_manager import DatabaseManager

load_dotenv()

SUPABASE_URL              = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

TEST_USER_ID = "33b11b04-55ee-4210-917b-9a5b86dc21c0"

# A fake user that has NO notifications — used to test empty state
EMPTY_USER_ID = "00000000-0000-0000-0000-000000000001"

pytestmark = pytest.mark.skipif(
    not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]),
    reason="Missing Supabase credentials in .env — skipping integration tests.",
)


# ─── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def supabase_client():
    return sb.create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


@pytest.fixture(scope="module")
def facade(supabase_client):
    return LuminFacade(supabase_client)


@pytest.fixture(scope="module")
def db(supabase_client):
    return DatabaseManager(supabase_client)


@pytest.fixture(autouse=True)
def cleanup(db):
    """
    Clean up test notifications after every test.
    Keeps the DB in a predictable state between tests.
    """
    yield
    db.supabase.table("notification") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .eq("notification_type", "recommendation") \
        .execute()

    db.supabase.table("recommendation") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .execute()


def _generate_recommendation(facade):
    """Helper: generate one general recommendation for the test user."""
    facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: getNotifications — Response Structure
#
#  WHAT WE TEST:
#    getNotifications() always returns a valid response structure,
#    even when there are no notifications.
#
#  WHY THIS MATTERS:
#    The Flutter app reads success, code, and data directly.
#    A missing key crashes the app even if there are no notifications.
# ══════════════════════════════════════════════════════════════════

class TestGetNotificationsStructure:

    def test_returns_success_true(self, facade):
        result = facade.getNotifications(TEST_USER_ID)
        assert result.get("success") is True

    def test_returns_correct_code(self, facade):
        result = facade.getNotifications(TEST_USER_ID)
        assert result.get("code") == "NOTIFICATIONS_FETCHED"

    def test_data_field_is_a_list(self, facade):
        result = facade.getNotifications(TEST_USER_ID)
        assert isinstance(result.get("data"), list), \
            f"Expected data to be a list, got: {type(result.get('data'))}"

    def test_returns_empty_list_when_no_notifications(self, facade, db):
        # Make sure there are no notifications for this user first
        db.supabase.table("notification") \
            .delete() \
            .eq("user_id", TEST_USER_ID) \
            .execute()

        result = facade.getNotifications(TEST_USER_ID)
        assert result.get("data") == []

    def test_status_field_is_success(self, facade):
        result = facade.getNotifications(TEST_USER_ID)
        assert result.get("status") == "success"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: getNotifications — After Recommendation
#
#  WHAT WE TEST:
#    After viewRecommendations() is called, getNotifications()
#    includes the new notification in its response.
#
#  WHY THIS MATTERS:
#    This verifies the full chain:
#    viewRecommendations() → saves notification → getNotifications() returns it.
#    If the notification is saved but with wrong user_id, it won't appear here.
# ══════════════════════════════════════════════════════════════════

class TestGetNotificationsAfterRecommendation:

    def test_notification_appears_after_recommendation(self, facade):
        _generate_recommendation(facade)
        result = facade.getNotifications(TEST_USER_ID)
        assert len(result["data"]) >= 1, \
            "Expected at least 1 notification after generating a recommendation"

    def test_notification_type_is_recommendation(self, facade):
        _generate_recommendation(facade)
        result = facade.getNotifications(TEST_USER_ID)
        types = [n.get("notification_type") for n in result["data"]]
        assert "recommendation" in types, \
            f"Expected 'recommendation' type in notifications, got: {types}"

    def test_notification_has_required_fields(self, facade):
        _generate_recommendation(facade)
        result = facade.getNotifications(TEST_USER_ID)
        notif = result["data"][0]
        for field in ["user_id", "notification_type", "content", "timestamp"]:
            assert field in notif, f"Missing field '{field}' in notification"

    def test_two_recommendations_produce_two_notifications(self, facade):
        _generate_recommendation(facade)
        _generate_recommendation(facade)
        result = facade.getNotifications(TEST_USER_ID)
        rec_notifs = [n for n in result["data"] if n.get("notification_type") == "recommendation"]
        assert len(rec_notifs) >= 2, \
            f"Expected at least 2 notifications, got {len(rec_notifs)}"

    def test_all_notifications_belong_to_test_user(self, facade):
        _generate_recommendation(facade)
        result = facade.getNotifications(TEST_USER_ID)
        for notif in result["data"]:
            assert notif.get("user_id") == TEST_USER_ID, \
                f"Notification belongs to wrong user: {notif.get('user_id')}"

    def test_notifications_ordered_newest_first(self, facade):
        _generate_recommendation(facade)
        _generate_recommendation(facade)
        result = facade.getNotifications(TEST_USER_ID)
        timestamps = [
            datetime.fromisoformat(str(n["timestamp"]).replace("Z", "+00:00"))
            for n in result["data"]
            if n.get("timestamp")
        ]
        assert timestamps == sorted(timestamps, reverse=True), \
            "Notifications are not ordered newest-first"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: getLatestNotification
#
#  WHAT WE TEST:
#    getLatestNotification() returns the most recently created
#    notification, or an empty response when there are none.
#
#  WHY THIS MATTERS:
#    The Flutter Home page calls this to show the latest alert.
#    Wrong ordering = user sees an old notification as "latest".
#    Empty state must return a specific code, not crash.
# ══════════════════════════════════════════════════════════════════

class TestGetLatestNotification:

    def test_returns_empty_response_when_no_notifications(self, facade, db):
        db.supabase.table("notification") \
            .delete() \
            .eq("user_id", TEST_USER_ID) \
            .execute()

        result = facade.getLatestNotification(TEST_USER_ID)
        assert result.get("success") is False
        assert result.get("code") == "NO_NOTIFICATIONS"
        assert result.get("data") is None

    def test_returns_success_after_recommendation(self, facade):
        _generate_recommendation(facade)
        result = facade.getLatestNotification(TEST_USER_ID)
        assert result.get("success") is True

    def test_code_is_latest_notification_fetched(self, facade):
        _generate_recommendation(facade)
        result = facade.getLatestNotification(TEST_USER_ID)
        assert result.get("code") == "LATEST_NOTIFICATION_FETCHED"

    def test_data_is_a_dict(self, facade):
        _generate_recommendation(facade)
        result = facade.getLatestNotification(TEST_USER_ID)
        assert isinstance(result.get("data"), dict), \
            f"Expected data to be a dict, got: {type(result.get('data'))}"

    def test_returns_most_recent_notification(self, facade):
        # Generate two recommendations — latest must be the second one
        _generate_recommendation(facade)
        _generate_recommendation(facade)

        all_notifs = facade.getNotifications(TEST_USER_ID)["data"]
        latest_result = facade.getLatestNotification(TEST_USER_ID)

        # The latest in getNotifications (index 0) must match getLatestNotification
        if all_notifs:
            assert all_notifs[0].get("content") == latest_result["data"].get("content"), \
                "getLatestNotification does not return the most recent notification"

    def test_latest_notification_has_required_fields(self, facade):
        _generate_recommendation(facade)
        result = facade.getLatestNotification(TEST_USER_ID)
        data = result.get("data", {})
        for field in ["user_id", "notification_type", "content", "timestamp"]:
            assert field in data, f"Missing field '{field}' in latest notification"

    def test_latest_notification_belongs_to_correct_user(self, facade):
        _generate_recommendation(facade)
        result = facade.getLatestNotification(TEST_USER_ID)
        assert result["data"].get("user_id") == TEST_USER_ID

    def test_latest_notification_type_is_recommendation(self, facade):
        _generate_recommendation(facade)
        result = facade.getLatestNotification(TEST_USER_ID)
        assert result["data"].get("notification_type") == "recommendation"
