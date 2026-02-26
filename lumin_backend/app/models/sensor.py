from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class SensorReadingIn(BaseModel):
    device_id: UUID
    kwh: float
    recorded_at: Optional[datetime] = None


class SensorReadingOut(BaseModel):
    id: UUID
    user_id: UUID
    device_id: UUID
    kwh: float
    recorded_at: datetime

    class Config:
        from_attributes = True

# lumin_backend/app/models/sensor.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional


# Represents SensorDataReading in the Class Diagram
@dataclass
class SensorDataReading:
    reading_id: int
    timestamp: datetime
    value: float
    unit: str
    device_id: int

    def ReadData(self):
        pass


# Represents SensorData in the Class Diagram
@dataclass
class SensorData:
    device_id: int
    readings: List[SensorDataReading]

    # + storeReading(reading: SensorDataReading): void
    def storeReading(self, reading: SensorDataReading) -> None:
        self.readings.append(reading)

    # + getLatestReading(): SensorDataReading
    def getLatestReading(self) -> Optional[SensorDataReading]:
        if not self.readings:
            return None
        return max(self.readings, key=lambda r: r.timestamp)

    # + getReadingsByDateRange(startDate: Date, endDate: Date): List<SensorDataReading>
    def getReadingsByDateRange(self, startDate: date, endDate: date) -> List[SensorDataReading]:
        return [
            r for r in self.readings
            if startDate <= r.timestamp.date() <= endDate
        ]