# lumin_backend/app/models/device.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List

from app.models.observer import Observer


@dataclass
class Device:
    device_id: int
    device_name: str
    device_type: str
    installation_date: date
    user_id: int

    # - observers: List<Observer>
    observers: List[Observer] = field(default_factory=list)

    # +collectSensorData():void
    def collectSensorData(self) -> None:
        return None

    # +getDeviceInfo():string
    def getDeviceInfo(self) -> str:
        return f"{self.device_name} ({self.device_type})"

    # +updateDeviceInfo(newvalue:string):void
    def updateDeviceInfo(self, newvalue: str) -> None:
        self.device_name = newvalue
        return None

    # + attach(o: Observer): void
    def attach(self, o: Observer) -> None:
        if o not in self.observers:
            self.observers.append(o)

    # + detach(o: Observer): void
    def detach(self, o: Observer) -> None:
        if o in self.observers:
            self.observers.remove(o)

    # + notifyObservers():void
    def notifyObservers(self) -> None:
        for o in self.observers:
            o.update(self)


# consumptionDevice extends Device
@dataclass
class consumptionDevice(Device):
    consumption_kwh: float = 0.0
    power_rating: float = 0.0

    # + getDeviceInfo(): String
    def getDeviceInfo(self) -> str:
        return f"{self.device_name} (consumption) - {self.consumption_kwh} kWh"

    # + getConsumption():float
    def getConsumption(self) -> float:
        return float(self.consumption_kwh)


# productionDevice extends Device
@dataclass
class productionDevice(Device):
    production_kwh: float = 0.0

    # +getDeviceInfo():string
    def getDeviceInfo(self) -> str:
        return f"{self.device_name} (production) - {self.production_kwh} kWh"

    # -getProduction():float  (مكتوبة بالسالب في الرسم بس هي دالة عادي)
    def getProduction(self) -> float:
        return float(self.production_kwh)