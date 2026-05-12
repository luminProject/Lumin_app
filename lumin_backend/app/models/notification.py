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

        try:
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

        except Exception:
            return "notification_not_sent"

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
    # SOLAR FORECAST — Solar Forecast Feature
    #
    # Three factory methods used by SolarForecast._send_notification().
    # Each embeds a dedup key as a suffix in the content string.
    # The key is stripped before display in Flutter (NotificationsPage
    # uses replaceAll(RegExp(r'\s*#\w[\w-]*$')) to remove it).
    #
    # Dedup key formats:
    #   forecast_ready   → #{season}_{year}       e.g. #spring_2026
    #   device_warning   → #warn_{YYYYMMDD}       e.g. #warn_20260501
    #   feature_disabled → #offline_since_{YYYYMMDD}
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
        Creates a forecast_ready notification.

        Input:
        user_id    : str — target user UUID
        season     : str — season name e.g. "spring"
        emoji      : str — season emoji e.g. "🌸"
        season_key : str — dedup key suffix e.g. "spring_2026"

        Output:
        Notification with type='forecast_ready' and dedup key embedded in content.
        Sent once per season when the previous season has ≥ 45 collected days.
        """
        cap     = season.capitalize()
        content = (
            f"Your {cap} {emoji} solar forecast is ready! "
            f"View your personalized production predictions "
            f"for the next year. #{season_key}"
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
        Creates a device_warning notification.

        Input:
        user_id              : str — target user UUID
        days_offline         : int — consecutive days without a solar reading
        today_str            : str — today formatted as YYYYMMDD (used as dedup key)
        feature_disable_days : int — days until forecast pauses (constant = 15)

        Output:
        Notification with type='device_warning' and dedup key #warn_{today_str}.
        Sent once per day for days 1–14 of consecutive offline.
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
        Creates a feature_disabled notification.

        Input:
        user_id                : str — target user UUID
        days_offline           : int — total consecutive offline days (≥ 15)
        last_reading_date_str  : str — last known reading date as YYYYMMDD

        Output:
        Notification with type='feature_disabled' and dedup key
        #offline_since_{last_reading_date_str}.
        Sent once per offline cycle when days_offline reaches 15.
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
    # END OF SOLAR FORECAST
    # =========================================================
    
    
    # =========================================================
    # Push title / body (used by FCM for all notification types)
    # =========================================================

    def getPushTitle(self) -> str:
        titles = {
            "recommendation":  "💡 Lumin Recommendation",
            "bill_warning":    "⚠️ Bill Warning",
            "bill_update":     "🔔 Bill Update",
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