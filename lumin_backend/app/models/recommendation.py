# lumin_backend/app/models/recommendation.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Recommendation:
    recommendation_id: Optional[int]
    recommendation_text: str
    timestamp: datetime
    user_id: str
    device_id: Optional[int] = None

    # +generateRecommendation(consumptionHistory:float):string
    def generateRecommendation(self, consumptionHistory: float) -> str:
        return self.recommendation_text

    # +sendRecommendation():string
    def sendRecommendation(self) -> str:
        return self.recommendation_text

    # +getData():float
    def getData(self) -> float:
        return 0.0

    # +update():void
    def update(self) -> None:
        return None