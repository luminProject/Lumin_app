from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Notification:
    """
    Notification model.
    Holds state and provides logic for building/sending notifications.
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
    # New factories (used by recommendations feature)
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
    # Push title / body (used by FCM)
    # =========================================================

    def getPushTitle(self) -> str:
        if self.notification_type == "recommendation":
            return "💡 Lumin Recommendation"
        if self.notification_type == "bill_warning":
            return "⚠️ Bill Warning"
        return "Lumin"

    def getPushBody(self) -> str:
        return self.content[:100] if self.content else ""

    # =========================================================
    # Build payload for DB insert (used by recommendations feature via DatabaseManager)
    # =========================================================

    def build_db_payload(self) -> dict:
        return {
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }