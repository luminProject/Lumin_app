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


class SmartEnergyFacade:
    """
    Facade layer:
    Routes (and the frontend indirectly) should call this single entry point
    instead of orchestrating multiple models/services directly.
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    # -----------------------------
    # Sensor reading ingestion
    # -----------------------------
    def ingest_sensor_reading(
        self,
        *,
        device_id: int,
        kwh_value: float,
        reading_time_iso: str,
    ) -> dict:
        # Verify device exists
        device_res = (
            self.supabase.table("device")
            .select("user_id")
            .eq("device_id", device_id)
            .limit(1)
            .execute()
        )

        if not device_res.data:
            raise ValueError("Device not found")

        row = {
            "device_id": device_id,
            "reading_time": reading_time_iso,
            "kwh_value": float(kwh_value),
        }

        result = self.supabase.table("sensor_data").insert(row).execute()
        return {"status": "stored", "data": result.data}

    # -----------------------------
    # Energy aggregation
    # -----------------------------
    def get_energy(self, *, user_id: str) -> dict:
        # Fetch user's devices
        devices_res = (
            self.supabase.table("device")
            .select("device_id")
            .eq("user_id", user_id)
            .execute()
        )

        if not devices_res.data:
            raise ValueError("No devices found")

        device_ids = [
            d["device_id"]
            for d in devices_res.data
            if d.get("device_id") is not None
        ]

        if not device_ids:
            raise ValueError("No valid device_id found")

        # Fetch sensor readings for these devices
        result = (
            self.supabase.table("sensor_data")
            .select("kwh_value, reading_time, device_id")
            .in_("device_id", device_ids)
            .order("reading_time", desc=True)
            .execute()
        )

        if not result.data:
            raise ValueError("No energy data found")

        total_today = sum(float(i.get("kwh_value") or 0) for i in result.data)

        return {
            "user_id": user_id,
            "total_kwh_today": total_today,
            "latest": result.data[0],
        }