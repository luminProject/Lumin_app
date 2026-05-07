"""
tests/test_notification_model.py
==================================
Unit tests for the Notification model — used by the recommendations
feature, bill warning feature, and solar forecast feature.

HOW TO RUN:
  cd lumin_backend
  python -m pytest tests/test_notification_model.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.models.notification import Notification


def _make_notification(notification_type="general", content="Test content",
                       user_id="user-123", supabase=None) -> Notification:
    return Notification(
        notification_id=None, user_id=user_id,
        notification_type=notification_type, content=content,
        timestamp=datetime.now(timezone.utc), supabase=supabase,
    )


class TestSendNotification:
    def test_no_supabase_returns_not_sent(self):
        assert _make_notification(supabase=None).sendNotification() == "notification_not_sent"

    def test_with_supabase_returns_sent(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"notification_id": 42}]
        assert _make_notification(supabase=mock_sb).sendNotification() == "notification_sent"

    def test_notification_id_updated_after_send(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"notification_id": 99}]
        notif = _make_notification(supabase=mock_sb)
        notif.sendNotification()
        assert notif.notification_id == 99

    def test_empty_data_keeps_id_none(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
        notif = _make_notification(supabase=mock_sb)
        notif.sendNotification()
        assert notif.notification_id is None

    def test_inserts_into_notification_table(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
        _make_notification(supabase=mock_sb).sendNotification()
        mock_sb.table.assert_called_with("notification")

    def test_insert_payload_has_required_fields(self):
        mock_sb = MagicMock()
        insert_mock = mock_sb.table.return_value.insert
        insert_mock.return_value.execute.return_value.data = []
        _make_notification(supabase=mock_sb, content="X", notification_type="bill_warning").sendNotification()
        inserted = insert_mock.call_args[0][0]
        for key in ["user_id", "content", "notification_type", "timestamp"]:
            assert key in inserted


class TestGetSetContent:
    def test_get_content(self):
        assert _make_notification(content="Hello").getContent() == "Hello"

    def test_set_content_updates(self):
        notif = _make_notification(content="Old")
        notif.setContent("New")
        assert notif.content == "New"

    def test_get_after_set(self):
        notif = _make_notification(content="Old")
        notif.setContent("Updated")
        assert notif.getContent() == "Updated"

    def test_set_empty_string(self):
        notif = _make_notification(content="X")
        notif.setContent("")
        assert notif.getContent() == ""


class TestToDict:
    def test_has_required_keys(self):
        result = _make_notification().to_dict()
        for key in ["user_id", "notification_type", "content", "timestamp"]:
            assert key in result

    def test_user_id_correct(self):
        assert _make_notification(user_id="abc").to_dict()["user_id"] == "abc"

    def test_type_correct(self):
        assert _make_notification(notification_type="bill_warning").to_dict()["notification_type"] == "bill_warning"

    def test_content_correct(self):
        assert _make_notification(content="msg").to_dict()["content"] == "msg"

    def test_timestamp_is_iso(self):
        ts = _make_notification().to_dict()["timestamp"]
        assert datetime.fromisoformat(ts) is not None

    def test_no_notification_id(self):
        assert "notification_id" not in _make_notification().to_dict()


class TestForRecommendation:
    def test_type_is_recommendation(self):
        assert Notification.forRecommendation("u1", "tip").notification_type == "recommendation"

    def test_user_id_set(self):
        assert Notification.forRecommendation("u99", "tip").user_id == "u99"

    def test_content_set(self):
        assert Notification.forRecommendation("u1", "My tip").content == "My tip"

    def test_notification_id_none(self):
        assert Notification.forRecommendation("u1", "tip").notification_id is None

    def test_supabase_none(self):
        assert Notification.forRecommendation("u1", "tip").supabase is None

    def test_timestamp_timezone_aware(self):
        assert Notification.forRecommendation("u1", "tip").timestamp.tzinfo is not None


class TestForForecastReady:
    def test_type_is_forecast_ready(self):
        assert Notification.forForecastReady("u1", "spring", "🌸", "spring_2026").notification_type == "forecast_ready"

    def test_user_id_set(self):
        assert Notification.forForecastReady("u42", "spring", "🌸", "spring_2026").user_id == "u42"

    def test_content_contains_capitalized_season(self):
        notif = Notification.forForecastReady("u1", "spring", "🌸", "spring_2026")
        assert "Spring" in notif.content

    def test_content_contains_emoji(self):
        notif = Notification.forForecastReady("u1", "spring", "🌸", "spring_2026")
        assert "🌸" in notif.content

    def test_content_contains_dedup_key(self):
        notif = Notification.forForecastReady("u1", "spring", "🌸", "spring_2026")
        assert "#spring_2026" in notif.content

    def test_notification_id_none(self):
        assert Notification.forForecastReady("u1", "summer", "☀️", "summer_2026").notification_id is None

    def test_supabase_none(self):
        assert Notification.forForecastReady("u1", "winter", "❄️", "winter_2026").supabase is None

    def test_different_seasons_capitalize_correctly(self):
        for season in ["spring", "summer", "autumn", "winter"]:
            notif = Notification.forForecastReady("u1", season, "🌿", f"{season}_2026")
            assert season.capitalize() in notif.content


class TestForDeviceWarning:
    def test_type_is_device_warning(self):
        assert Notification.forDeviceWarning("u1", 3, "20260505", 15).notification_type == "device_warning"

    def test_user_id_set(self):
        assert Notification.forDeviceWarning("u7", 1, "20260505", 15).user_id == "u7"

    def test_content_contains_days_offline(self):
        notif = Notification.forDeviceWarning("u1", 5, "20260505", 15)
        assert "5" in notif.content

    def test_content_contains_feature_disable_days(self):
        notif = Notification.forDeviceWarning("u1", 3, "20260505", 15)
        assert "15" in notif.content

    def test_content_contains_dedup_key(self):
        notif = Notification.forDeviceWarning("u1", 3, "20260505", 15)
        assert "#warn_20260505" in notif.content

    def test_notification_id_none(self):
        assert Notification.forDeviceWarning("u1", 1, "20260505", 15).notification_id is None

    def test_supabase_none(self):
        assert Notification.forDeviceWarning("u1", 1, "20260505", 15).supabase is None


class TestForFeatureDisabled:
    def test_type_is_feature_disabled(self):
        assert Notification.forFeatureDisabled("u1", 15, "20260420").notification_type == "feature_disabled"

    def test_user_id_set(self):
        assert Notification.forFeatureDisabled("u5", 15, "20260420").user_id == "u5"

    def test_content_contains_days_offline(self):
        notif = Notification.forFeatureDisabled("u1", 20, "20260420")
        assert "20" in notif.content

    def test_content_contains_dedup_key(self):
        notif = Notification.forFeatureDisabled("u1", 15, "20260420")
        assert "#offline_since_20260420" in notif.content

    def test_notification_id_none(self):
        assert Notification.forFeatureDisabled("u1", 15, "20260420").notification_id is None

    def test_supabase_none(self):
        assert Notification.forFeatureDisabled("u1", 15, "20260420").supabase is None


class TestGetPushTitle:
    def test_recommendation_title(self):
        assert "💡" in _make_notification(notification_type="recommendation").getPushTitle()

    def test_bill_warning_title(self):
        assert "⚠️" in _make_notification(notification_type="bill_warning").getPushTitle()

    def test_forecast_ready_title(self):
        assert "☀️" in _make_notification(notification_type="forecast_ready").getPushTitle()

    def test_device_warning_title(self):
        notif = _make_notification(notification_type="device_warning")
        assert "⚠️" in notif.getPushTitle() or "Solar" in notif.getPushTitle()

    def test_feature_disabled_title(self):
        assert "🚫" in _make_notification(notification_type="feature_disabled").getPushTitle()

    def test_unknown_type_returns_fallback(self):
        assert _make_notification(notification_type="something_else").getPushTitle() == "🔔 Lumin"

    def test_general_type_returns_fallback(self):
        assert _make_notification(notification_type="general").getPushTitle() == "🔔 Lumin"

    def test_all_titles_are_strings(self):
        for t in ["recommendation", "bill_warning", "forecast_ready",
                  "device_warning", "feature_disabled", "general"]:
            assert isinstance(_make_notification(notification_type=t).getPushTitle(), str)


class TestGetPushBody:
    def test_short_content_as_is(self):
        assert _make_notification(content="Short tip").getPushBody() == "Short tip"

    def test_long_content_truncated_to_100(self):
        assert len(_make_notification(content="A" * 200).getPushBody()) == 100

    def test_exactly_100_not_truncated(self):
        text = "B" * 100
        assert _make_notification(content=text).getPushBody() == text

    def test_101_truncated_to_100(self):
        assert len(_make_notification(content="C" * 101).getPushBody()) == 100

    def test_empty_returns_empty(self):
        assert _make_notification(content="").getPushBody() == ""

    def test_returns_string(self):
        assert isinstance(_make_notification(content="Hello").getPushBody(), str)


class TestBuildDbPayload:
    def test_has_required_keys(self):
        result = _make_notification().build_db_payload()
        for key in ["user_id", "notification_type", "content", "timestamp"]:
            assert key in result

    def test_user_id_correct(self):
        assert _make_notification(user_id="xyz").build_db_payload()["user_id"] == "xyz"

    def test_type_correct(self):
        assert _make_notification(notification_type="recommendation").build_db_payload()["notification_type"] == "recommendation"

    def test_content_correct(self):
        assert _make_notification(content="Run at noon.").build_db_payload()["content"] == "Run at noon."

    def test_timestamp_is_iso(self):
        ts = _make_notification().build_db_payload()["timestamp"]
        assert datetime.fromisoformat(ts) is not None

    def test_no_notification_id(self):
        assert "notification_id" not in _make_notification().build_db_payload()

    def test_matches_to_dict(self):
        notif = _make_notification(user_id="u1", notification_type="recommendation", content="tip")
        payload = notif.build_db_payload()
        to_dict = notif.to_dict()
        assert payload["user_id"] == to_dict["user_id"]
        assert payload["notification_type"] == to_dict["notification_type"]
        assert payload["content"] == to_dict["content"]