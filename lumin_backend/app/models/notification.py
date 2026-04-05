from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class Notification:
    notification_id: Optional[int]
    user_id: str
    notification_type: str
    content: str
    timestamp: datetime
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

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }