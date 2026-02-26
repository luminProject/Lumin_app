# lumin_backend/app/core/interfaces.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Protocol, Optional, Any


# ---------- Observer Pattern (Device has observers: List<Observer>) ----------
class Observer(Protocol):
    def update(self, device: "Device") -> None: ...


# ---------- <<interface>> DeviceUpdateHandler ----------
class DeviceUpdateHandler(Protocol):
    device: "Device"
    def update(self, device: "Device") -> None: ...


# ---------- <<Interface>> ForcastModel (as written in diagram) ----------
class ForcastModel(Protocol):
    def train(self, history: Any, weatherHistory: Any) -> None: ...
    def predict(self, weather: "WeatherData") -> float: ...


# Forward-declared types (will be implemented in models files)
class Device: ...
class WeatherData: ...