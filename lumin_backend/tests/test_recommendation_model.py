"""
tests/test_notification_model.py
==================================
Unit tests for the Notification model — used by both the
recommendations feature and the bill warning feature.

WHY UNIT TESTS:
  The Notification model is shared between two features
  (recommendations and bill warning). These tests verify all
  methods without a real Supabase connection — DB calls are mocked.

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_notification_model.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.models.notification import Notification


# ── Helper ────────────────────────────────────────────────────────

def _make_notification(
    notification_type="general",
    content="Test content",
    user_id="user-123",
    supabase=None,
) -> Notification:
    return Notification(
        notification_id=None,
        user_id=user_id,
        notification_type=notification_type,
        content=content,
        timestamp=datetime.now(timezone.utc),
        supabase=supabase,
    )


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 1: sendNotification
#
#  WHAT WE TEST:
#    sendNotification() returns the right status string and
#    updates notification_id when Supabase returns data.
#    When supabase is None it must return "notification_not_sent".
#
#  WHY THIS MATTERS:
#    This method is used by the bill warning feature in the Facade.
#    If it silently fails without returning the correct status,
#    the Facade cannot know whether the notification was sent.
# ══════════════════════════════════════════════════════════════════

class TestSendNotification:

    def test_no_supabase_returns_not_sent(self):
        notif = _make_notification(supabase=None)
        result = notif.sendNotification()
        assert result == "notification_not_sent"

    def test_with_supabase_returns_sent(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"notification_id": 42}
        ]
        notif = _make_notification(supabase=mock_sb)
        result = notif.sendNotification()
        assert result == "notification_sent"

    def test_notification_id_is_updated_after_send(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"notification_id": 99}
        ]
        notif = _make_notification(supabase=mock_sb)
        notif.sendNotification()
        assert notif.notification_id == 99

    def test_empty_data_response_keeps_notification_id_none(self):
        # Supabase returns empty data (insert failed silently)
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
        notif = _make_notification(supabase=mock_sb)
        notif.sendNotification()
        assert notif.notification_id is None

    def test_supabase_insert_called_with_correct_table(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
        notif = _make_notification(supabase=mock_sb)
        notif.sendNotification()
        mock_sb.table.assert_called_with("notification")

    def test_insert_payload_contains_required_fields(self):
        mock_sb = MagicMock()
        insert_mock = mock_sb.table.return_value.insert
        insert_mock.return_value.execute.return_value.data = []
        notif = _make_notification(
            supabase=mock_sb,
            content="Test",
            notification_type="bill_warning",
            user_id="u-1",
        )
        notif.sendNotification()
        inserted = insert_mock.call_args[0][0]
        assert "user_id" in inserted
        assert "content" in inserted
        assert "notification_type" in inserted
        assert "timestamp" in inserted


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 2: getContent and setContent
#
#  WHAT WE TEST:
#    getContent() returns the content field.
#    setContent() updates the content field.
#
#  WHY THIS MATTERS:
#    Used by the bill warning in lumin_facade to build the warning
#    message before calling sendNotification().
#    If setContent doesn't persist, the wrong message gets sent.
# ══════════════════════════════════════════════════════════════════

class TestGetSetContent:

    def test_get_content_returns_current_content(self):
        notif = _make_notification(content="Hello")
        assert notif.getContent() == "Hello"

    def test_set_content_updates_content(self):
        notif = _make_notification(content="Old")
        notif.setContent("New message")
        assert notif.content == "New message"

    def test_get_content_after_set_returns_new_value(self):
        notif = _make_notification(content="Old")
        notif.setContent("Updated")
        assert notif.getContent() == "Updated"

    def test_set_content_empty_string(self):
        notif = _make_notification(content="Something")
        notif.setContent("")
        assert notif.getContent() == ""


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 3: to_dict
#
#  WHAT WE TEST:
#    to_dict() returns a dict with all required keys and correct values.
#    Used by the old notification flow (bill warning compatibility).
#
#  WHY THIS MATTERS:
#    The bill warning feature relies on this dict to insert into Supabase.
#    A missing key = runtime crash in the bill feature.
# ══════════════════════════════════════════════════════════════════

class TestToDict:

    def test_contains_all_required_keys(self):
        notif = _make_notification()
        result = notif.to_dict()
        for key in ["user_id", "notification_type", "content", "timestamp"]:
            assert key in result, f"Missing key: {key}"

    def test_user_id_is_correct(self):
        notif = _make_notification(user_id="abc-456")
        assert notif.to_dict()["user_id"] == "abc-456"

    def test_notification_type_is_correct(self):
        notif = _make_notification(notification_type="bill_warning")
        assert notif.to_dict()["notification_type"] == "bill_warning"

    def test_content_is_correct(self):
        notif = _make_notification(content="Your bill is high")
        assert notif.to_dict()["content"] == "Your bill is high"

    def test_timestamp_is_iso_string(self):
        notif = _make_notification()
        ts = notif.to_dict()["timestamp"]
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_notification_id_not_in_to_dict(self):
        # to_dict is for DB insert — notification_id is auto-generated
        notif = _make_notification()
        result = notif.to_dict()
        assert "notification_id" not in result


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 4: forRecommendation (factory)
#
#  WHAT WE TEST:
#    Class method that creates a ready-to-use Notification for
#    the recommendations feature. Must set type="recommendation".
#
#  WHY THIS MATTERS:
#    This factory is called by the Facade every time a recommendation
#    is generated. Wrong type = notification appears in wrong category
#    in the Flutter app.
# ══════════════════════════════════════════════════════════════════

class TestForRecommendation:

    def test_type_is_recommendation(self):
        notif = Notification.forRecommendation("u1", "Save energy tip.")
        assert notif.notification_type == "recommendation"

    def test_user_id_is_set(self):
        notif = Notification.forRecommendation("user-999", "tip")
        assert notif.user_id == "user-999"

    def test_content_is_set(self):
        notif = Notification.forRecommendation("u1", "My tip text")
        assert notif.content == "My tip text"

    def test_notification_id_is_none(self):
        # ID is assigned by DB after insert — must start as None
        notif = Notification.forRecommendation("u1", "tip")
        assert notif.notification_id is None

    def test_supabase_is_none(self):
        # Recommendations use DatabaseManager, not direct supabase
        notif = Notification.forRecommendation("u1", "tip")
        assert notif.supabase is None

    def test_timestamp_is_timezone_aware(self):
        notif = Notification.forRecommendation("u1", "tip")
        assert notif.timestamp.tzinfo is not None


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 5: getPushTitle
#
#  WHAT WE TEST:
#    getPushTitle() returns the correct FCM notification title
#    for each notification type.
#
#  WHY THIS MATTERS:
#    This is the title the user sees on their phone lock screen.
#    Wrong title for bill_warning = confusing UX.
#    "Lumin" fallback must work for unknown types.
# ══════════════════════════════════════════════════════════════════

class TestGetPushTitle:

    def test_recommendation_type_returns_recommendation_title(self):
        notif = _make_notification(notification_type="recommendation")
        assert "Recommendation" in notif.getPushTitle() or "💡" in notif.getPushTitle()

    def test_bill_warning_type_returns_bill_title(self):
        notif = _make_notification(notification_type="bill_warning")
        assert "Bill" in notif.getPushTitle() or "⚠️" in notif.getPushTitle()

    def test_general_type_returns_lumin(self):
        notif = _make_notification(notification_type="general")
        assert notif.getPushTitle() == "🔔 Lumin"

    def test_unknown_type_returns_lumin(self):
        notif = _make_notification(notification_type="something_else")
        assert notif.getPushTitle() == "🔔 Lumin"

    def test_title_is_string(self):
        for t in ["recommendation", "bill_warning", "general"]:
            notif = _make_notification(notification_type=t)
            assert isinstance(notif.getPushTitle(), str)


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 6: getPushBody
#
#  WHAT WE TEST:
#    getPushBody() returns the content truncated to 100 characters.
#    Empty content must return empty string, not crash.
#
#  WHY THIS MATTERS:
#    FCM push notifications have character limits. Sending a very
#    long body can cause the notification to fail or display wrongly.
#    Empty content must be handled gracefully.
# ══════════════════════════════════════════════════════════════════

class TestGetPushBody:

    def test_short_content_returned_as_is(self):
        notif = _make_notification(content="Short tip")
        assert notif.getPushBody() == "Short tip"

    def test_long_content_truncated_to_100_chars(self):
        long_text = "A" * 200
        notif = _make_notification(content=long_text)
        result = notif.getPushBody()
        assert len(result) == 100

    def test_exactly_100_chars_not_truncated(self):
        text = "B" * 100
        notif = _make_notification(content=text)
        assert notif.getPushBody() == text

    def test_101_chars_truncated_to_100(self):
        text = "C" * 101
        notif = _make_notification(content=text)
        assert len(notif.getPushBody()) == 100

    def test_empty_content_returns_empty_string(self):
        notif = _make_notification(content="")
        assert notif.getPushBody() == ""

    def test_returns_string_type(self):
        notif = _make_notification(content="Hello")
        assert isinstance(notif.getPushBody(), str)


# ══════════════════════════════════════════════════════════════════
#  TEST CLASS 7: build_db_payload
#
#  WHAT WE TEST:
#    build_db_payload() returns the dict passed to DatabaseManager
#    for inserting into the notification table.
#
#  WHY THIS MATTERS:
#    The DatabaseManager inserts this dict directly into Supabase.
#    A missing key = insert fails. Wrong values = wrong data in DB.
#    Note: build_db_payload is used by recommendations feature,
#    to_dict() is used by bill warning — they must both work.
# ══════════════════════════════════════════════════════════════════

class TestBuildDbPayload:

    def test_contains_all_required_keys(self):
        notif = _make_notification()
        result = notif.build_db_payload()
        for key in ["user_id", "notification_type", "content", "timestamp"]:
            assert key in result, f"Missing key: {key}"

    def test_user_id_is_correct(self):
        notif = _make_notification(user_id="xyz-789")
        assert notif.build_db_payload()["user_id"] == "xyz-789"

    def test_notification_type_is_correct(self):
        notif = _make_notification(notification_type="recommendation")
        assert notif.build_db_payload()["notification_type"] == "recommendation"

    def test_content_is_correct(self):
        notif = _make_notification(content="Run appliances at noon.")
        assert notif.build_db_payload()["content"] == "Run appliances at noon."

    def test_timestamp_is_iso_string(self):
        notif = _make_notification()
        ts = notif.build_db_payload()["timestamp"]
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_notification_id_not_in_payload(self):
        # notification_id is auto-generated by DB — must not be in payload
        notif = _make_notification()
        result = notif.build_db_payload()
        assert "notification_id" not in result

    def test_build_db_payload_and_to_dict_match(self):
        # Both methods are used by different features —
        # they must return the same core data
        notif = _make_notification(
            user_id="u1",
            notification_type="recommendation",
            content="tip",
        )
        payload = notif.build_db_payload()
        to_dict = notif.to_dict()
        assert payload["user_id"]            == to_dict["user_id"]
        assert payload["notification_type"]  == to_dict["notification_type"]
        assert payload["content"]            == to_dict["content"]