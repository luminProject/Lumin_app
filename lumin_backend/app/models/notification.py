from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Notification:
    notification_id: Optional[int]
    user_id: str
    notification_type: str
    content: str
    timestamp: datetime

    def sendNotification(self) -> str:
        return self.content

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