from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Notification:
    # attributes (نفس الأسماء الشائعة بالدايقرام)
    notification_id: int
    message: str
    timestamp: datetime
    user_id: int

    # +send(): void
    def send(self) -> None:
        return None

    # +markAsRead(): void
    def markAsRead(self) -> None:
        return None
