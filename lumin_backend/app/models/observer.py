# lumin_backend/app/models/observer.py
from __future__ import annotations

from typing import Protocol


# ✅ مطابق لفكرة الـ Observer في الـ class diagram
class Observer(Protocol):
    # +update(): void
    def update(self, o=None) -> None:
        ...
