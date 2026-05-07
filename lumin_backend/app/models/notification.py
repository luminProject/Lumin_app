from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Notification:
    """
    Notification model.
    Holds state and provides logic for building/sending notifications.

    Notification types in the system:
      bill_warning      — bill predicted to exceed limit (BillPrediction)
      bill_update       — bill checkpoint update (BillPrediction)
      recommendation    — energy saving tip (Recommendation feature)
      forecast_ready    — previous season data complete, forecast available (Solar Forecast)
      device_warning    — no solar data today, days 1–14 (Solar Forecast)
      feature_disabled  — device offline ≥ 15 days, forecast paused (Solar Forecast)
    """

    notification_id: Optional[int]
    user_id: str
    notification_type: str
    content: str
    timestamp: datetime
    supabase: Any = None

    # =========================================================
    # Existing methods (used by bill warning — DO NOT REMOVE)
    # =========================================================

    def sendNotification(self) -> str:
        """
        Insert this notification into the database.
        Used by bill warning logic in lumin_facade.
        """
        if self.supabase is None:
            return "notification_not_sent"

        result = (
            self.supabase
            .table("notification")
            .insert({
                "user_id": self.user_id,
                "content": self.content,
                "notification_type": self.notification_type,
                "timestamp": self.timestamp.isoformat(),
            })
            .execute()
        )

        data = getattr(result, "data", None) or []
        if data:
            self.notification_id = int(data[0].get("notification_id") or 0)

        return "notification_sent"

    def getContent(self) -> str:
        return self.content

    def setContent(self, details: str) -> None:
        self.content = details

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }

    # =========================================================
    # Existing factory (used by recommendations feature)
    # =========================================================

    @classmethod
    def forRecommendation(cls, user_id: str, recommendation_text: str) -> "Notification":
        """Create a notification of type 'recommendation'."""
        return cls(
            notification_id=None,
            user_id=user_id,
            notification_type="recommendation",
            content=recommendation_text,
            timestamp=datetime.now(timezone.utc),
            supabase=None,
        )

    # =========================================================
    # Solar Forecast factories (Sprint 2)
    # ---------------------------------------------------------
    # Used by SolarForecastService and DeviceMonitor.
    # Content embeds a dedup key as a suffix — stripped before
    # display in the app. See Change Log v4, Section 3.16.
    #
    # Dedup key formats:
    #   forecast_ready   → #season_name_year  (e.g. #spring_2026)
    #   device_warning   → #warn_YYYYMMDD
    #   feature_disabled → #offline_since_YYYYMMDD
    # =========================================================

    @classmethod
    def forForecastReady(
        cls,
        user_id: str,
        season: str,
        emoji: str,
        season_key: str,
    ) -> "Notification":
        """
        Create a forecast_ready notification.
        Sent once per season when ≥ 45 days of previous-season data exist.
        Dedup key: #{season_key} e.g. #spring_2026

        Parameters
        ----------
        season     : str — e.g. "spring"
        emoji      : str — season emoji e.g. "🌸"
        season_key : str — e.g. "spring_2026"
        """
        cap     = season.capitalize()
        content = (
            f"Your {cap} {emoji} solar forecast is ready! "
            f"View your personalized production predictions "
            f"for the next 2 years. #{season_key}"
        )
        return cls(
            notification_id=None,
            user_id=user_id,
            notification_type="forecast_ready",
            content=content,
            timestamp=datetime.now(timezone.utc),
            supabase=None,
        )

    @classmethod
    def forDeviceWarning(
        cls,
        user_id: str,
        days_offline: int,
        today_str: str,
        feature_disable_days: int,
    ) -> "Notification":
        """
        Create a device_warning notification.
        Sent once per missed day (days 1–14).
        Dedup key: #warn_YYYYMMDD

        Parameters
        ----------
        days_offline         : int — number of consecutive offline days
        today_str            : str — YYYYMMDD formatted string of today
        feature_disable_days : int — threshold before forecast pauses (15)
        """
        content = (
            f"No solar data received today. "
            f"We couldn't read your production device. "
            f"Check your connection. "
            f"Day {days_offline} of {feature_disable_days} before forecast pauses. "
            f"#warn_{today_str}"
        )
        return cls(
            notification_id=None,
            user_id=user_id,
            notification_type="device_warning",
            content=content,
            timestamp=datetime.now(timezone.utc),
            supabase=None,
        )

    @classmethod
    def forFeatureDisabled(
        cls,
        user_id: str,
        days_offline: int,
        last_reading_date_str: str,
    ) -> "Notification":
        """
        Create a feature_disabled notification.
        Sent once per offline cycle when days_offline ≥ 15.
        Dedup key: #offline_since_YYYYMMDD

        Parameters
        ----------
        days_offline           : int — total consecutive offline days
        last_reading_date_str  : str — YYYYMMDD of last known reading
        """
        content = (
            f"Solar Forecast has been paused. "
            f"Your device has been offline for {days_offline} days. "
            f"Reconnect to resume data collection. "
            f"#offline_since_{last_reading_date_str}"
        )
        return cls(
            notification_id=None,
            user_id=user_id,
            notification_type="feature_disabled",
            content=content,
            timestamp=datetime.now(timezone.utc),
            supabase=None,
        )

    # =========================================================
    # Push title / body (used by FCM for all notification types)
    # =========================================================

    def getPushTitle(self) -> str:
        titles = {
            "recommendation":  "💡 Lumin Recommendation",
            "bill_warning":    "⚠️ Bill Warning",
            "forecast_ready":  "☀️ Solar Forecast Ready",
            "device_warning":  "⚠️ No Solar Data Today",
            "feature_disabled": "🚫 Solar Forecast Paused",
        }
        return titles.get(self.notification_type, "🔔 Lumin")

    def getPushBody(self) -> str:
        return self.content[:100] if self.content else ""

    # =========================================================
    # Build payload for DB insert (used via DatabaseManager)
    # =========================================================

    def build_db_payload(self) -> dict:
        return {
            "user_id":           self.user_id,
            "notification_type": self.notification_type,
            "content":           self.content,
            "timestamp":         self.timestamp.isoformat(),
        }