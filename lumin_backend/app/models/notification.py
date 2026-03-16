
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Notification:
    notification_id: int
    content: str
    notification_type: str
    timestamp: datetime
    user_id: str
    supabase: Any = None

    def sendNotification(self) -> str:
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
        return None    # +send(): void
    def send(self) -> None:
        return None

    # +markAsRead(): void
    def markAsRead(self) -> None:
        return None