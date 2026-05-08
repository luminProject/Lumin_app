"""
tests/test_recommendation_integration.py
==========================================
Integration tests for the Recommendations + Notifications feature.

Integration level:
  LuminFacade <-> DatabaseManager <-> Recommendation Model
              <-> Notification Model <-> Supabase DB

What these tests verify:
  - After viewRecommendations() → a row is saved in the recommendation table
  - After viewRecommendations() → a row is saved in the notification table
  - The saved recommendation text is non-empty
  - The saved notification type is "recommendation"
  - The notification content matches the recommendation text
  - viewRecommendations(type="general") always generates a general rec
  - viewRecommendations(type="solar") falls back to general if no solar data

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_recommendation_integration.py -v

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

SUPABASE_URL             = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ── Change this to any valid user_id in your Supabase users table ──
TEST_USER_ID = "33b11b04-55ee-4210-917b-9a5b86dc21c0"

pytestmark = pytest.mark.skipif(
    not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]),
    reason="Missing Supabase credentials in .env — skipping integration tests.",
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


@pytest.fixture(autouse=True)
def cleanup(db):
    """
    Delete all test recommendations and notifications created during each test.
    Runs after every test automatically (autouse=True).
    This keeps the DB clean between tests.
    """
    yield
    # Cleanup after test
    db.supabase.table("recommendation") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .execute()

    db.supabase.table("notification") \
        .delete() \
        .eq("user_id", TEST_USER_ID) \
        .eq("notification_type", "recommendation") \
        .execute()


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: General Recommendation Flow
#
#  WHAT WE TEST:
#    viewRecommendations(type="general") must:
#      1. Return success=True
#      2. Save a row in the recommendation table
#      3. Save a row in the notification table
#      4. The notification content must match the recommendation text
#
#  WHY THIS MATTERS:
#    This is the full integration of Facade + DatabaseManager + Supabase.
#    Unit tests already verified the model logic — here we verify the
#    real DB write happens correctly end-to-end.
# ══════════════════════════════════════════════════════════════════

class TestGeneralRecommendationFlow:

    def test_returns_success_true(self, facade):
        result = facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        assert result.get("success") is True, \
            f"Expected success=True, got: {result}"

    def test_recommendation_row_saved_in_db(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        row = db.get_latest_recommendation(TEST_USER_ID)
        assert row is not None, "No recommendation row found in DB after viewRecommendations()"

    def test_recommendation_text_is_not_empty(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        row = db.get_latest_recommendation(TEST_USER_ID)
        assert row is not None
        text = row.get("recommendation_text", "")
        assert len(text) > 5, f"Recommendation text is too short: '{text}'"

    def test_recommendation_belongs_to_correct_user(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        row = db.get_latest_recommendation(TEST_USER_ID)
        assert row is not None
        assert row.get("user_id") == TEST_USER_ID

    def test_notification_row_saved_in_db(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None, "No notification row found in DB after viewRecommendations()"

    def test_notification_type_is_recommendation(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None
        assert notif.get("notification_type") == "recommendation", \
            f"Expected type='recommendation', got: {notif.get('notification_type')}"

    def test_notification_content_matches_recommendation_text(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        rec   = db.get_latest_recommendation(TEST_USER_ID)
        notif = db.get_latest_notification(TEST_USER_ID)
        assert rec is not None and notif is not None
        assert rec.get("recommendation_text") == notif.get("content"), \
            "Notification content does not match recommendation text"

    def test_response_contains_recommendation_data(self, facade):
        result = facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        assert result.get("recommendation") is not None, \
            "Response should contain the saved recommendation row"

    def test_code_is_general_recommendation_generated(self, facade):
        result = facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        assert result.get("code") == "GENERAL_RECOMMENDATION_GENERATED"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: Solar Recommendation — Fallback to General
#
#  WHAT WE TEST:
#    viewRecommendations(type="solar") for a user with no solar data
#    must fall back gracefully to a general recommendation.
#    The DB must still have a recommendation + notification row.
#
#  WHY THIS MATTERS:
#    The fallback logic is critical — if solar data is missing,
#    the user must still receive a recommendation, not an empty response.
#    This verifies the full fallback chain works end-to-end.
# ══════════════════════════════════════════════════════════════════

class TestSolarRecommendationFallback:

    def test_solar_request_returns_success(self, facade):
        # Whether solar or fallback, the result must be success
        result = facade.viewRecommendations(TEST_USER_ID, recommendation_type="solar")
        assert result.get("success") is True

    def test_solar_fallback_saves_recommendation_in_db(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="solar")
        row = db.get_latest_recommendation(TEST_USER_ID)
        assert row is not None, "No recommendation row after solar request"

    def test_solar_fallback_saves_notification_in_db(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="solar")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None, "No notification row after solar request"

    def test_solar_fallback_notification_type_is_recommendation(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="solar")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None
        assert notif.get("notification_type") == "recommendation"


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: Two Consecutive Calls
#
#  WHAT WE TEST:
#    Calling viewRecommendations() twice creates two separate rows.
#    Both rows belong to the correct user.
#    The notification table also has two rows.
#
#  WHY THIS MATTERS:
#    Verifies that each call correctly inserts a new row independently.
#    No dedup/overwrite logic should merge them — each call is independent.
# ══════════════════════════════════════════════════════════════════

class TestConsecutiveCalls:

    def test_two_calls_create_two_recommendation_rows(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")

        rows = db.get_all_recommendations(TEST_USER_ID)
        assert len(rows) >= 2, \
            f"Expected at least 2 recommendation rows, got {len(rows)}"

    def test_two_calls_create_two_notification_rows(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")

        notifs = db.get_user_notifications(TEST_USER_ID)
        rec_notifs = [n for n in notifs if n.get("notification_type") == "recommendation"]
        assert len(rec_notifs) >= 2, \
            f"Expected at least 2 notification rows, got {len(rec_notifs)}"

    def test_both_rows_belong_to_test_user(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")

        rows = db.get_all_recommendations(TEST_USER_ID)
        for row in rows:
            assert row.get("user_id") == TEST_USER_ID


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 4: DB Row Structure
#
#  WHAT WE TEST:
#    The saved rows in recommendation and notification tables
#    have all the required columns with correct types.
#
#  WHY THIS MATTERS:
#    The Flutter app reads specific fields from these rows.
#    A missing column = crash in the app when displaying recommendations.
# ══════════════════════════════════════════════════════════════════

class TestDbRowStructure:

    def test_recommendation_row_has_required_columns(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        row = db.get_latest_recommendation(TEST_USER_ID)
        assert row is not None
        for col in ["user_id", "recommendation_text", "timestamp"]:
            assert col in row, f"Missing column in recommendation row: '{col}'"

    def test_recommendation_timestamp_is_valid(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        row = db.get_latest_recommendation(TEST_USER_ID)
        assert row is not None
        ts = row.get("timestamp")
        assert ts is not None, "timestamp is None"
        # Must be parseable as a datetime
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        assert parsed is not None

    def test_notification_row_has_required_columns(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None
        for col in ["user_id", "notification_type", "content", "timestamp"]:
            assert col in notif, f"Missing column in notification row: '{col}'"

    def test_notification_user_id_matches(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None
        assert notif.get("user_id") == TEST_USER_ID

    def test_notification_content_is_not_empty(self, facade, db):
        facade.viewRecommendations(TEST_USER_ID, recommendation_type="general")
        notif = db.get_latest_notification(TEST_USER_ID)
        assert notif is not None
        content = notif.get("content", "")
        assert len(content) > 5, f"Notification content too short: '{content}'"
