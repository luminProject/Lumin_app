

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Protocol


# =========================
# WeatherData
# (الكلاس دايقرام ما كتب Attributes، فحطّيناه كـ container عام)
# =========================
@dataclass
class WeatherData:
    """Represents weather inputs used by prediction models.

    NOTE: The class diagram does not specify exact fields.
    We keep it flexible to avoid breaking changes later.
    """

    data: Dict[str, Any] = field(default_factory=dict)


# =========================
# <<Interface>> ForcastModel
# =========================
class ForcastModel(Protocol):
    def train(self, history: List[Any], weatherHistory: List[WeatherData]) -> None:
        ...

    def predict(self, weather: WeatherData) -> float:
        ...


# =========================
# WeightedSolarModel
# =========================
@dataclass
class WeightedSolarModel:
    # - weights: Map<String, Float>
    weights: Dict[str, float] = field(default_factory=dict)

    # - bias: float
    bias: float = 0.0

    # - lastTrainingDate: Date
    lastTrainingDate: Optional[date] = None

    # + method(type): type
    def method(self, type: Any) -> Any:
        # الكلاس دايقرام ما وضّح الوظيفة، نخليه يرجع نفس الـ type كـ placeholder
        return type

    # + train(history: List)
    def train(self, history: List[Any]) -> None:
        # تدريب بسيط Placeholder
        self.lastTrainingDate = date.today()

    # + predict(weather: WeatherData): float
    def predict(self, weather: WeatherData) -> float:
        # Placeholder بسيط: لو عندنا weights نطبقها على values الرقمية داخل weather.data
        total = self.bias
        for k, w in self.weights.items():
            v = weather.data.get(k)
            if isinstance(v, (int, float)):
                total += float(v) * float(w)
        return float(total)


# =========================
# SolarForecast
# =========================
@dataclass
class SolarForecast:
    # -forecast_id:int
    forecast_id: int

    # -predicted_production_kwh:float
    predicted_production_kwh: float = 0.0

    # -confidence_level:float
    confidence_level: float = 0.0

    # - model: IPredictionModel
    # في الدايقرام مكتوب IPredictionModel، لكن الموجود كـ interface اسمه ForcastModel
    model: Optional[ForcastModel] = None

    # +generateForecast():void
    def generateForecast(self, weather: Optional[WeatherData] = None) -> None:
        if self.model is None:
            # لو ما فيه موديل، ما نقدر نتوقع
            self.predicted_production_kwh = 0.0
            self.confidence_level = 0.0
            return

        if weather is None:
            weather = WeatherData()

        self.predicted_production_kwh = float(self.model.predict(weather))
        # Placeholder للـ confidence
        self.confidence_level = 0.75

    # + trainModel(): void
    def trainModel(self, history: List[Any], weatherHistory: List[WeatherData]) -> None:
        if self.model is None:
            return
        self.model.train(history, weatherHistory)

    # + getResult(): float
    def getResult(self) -> float:
        return float(self.predicted_production_kwh)