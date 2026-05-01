from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from app.models.device import Device, consumptionDevice, productionDevice


class DeviceFactory:
    @staticmethod
    def _parse_installation_date(value: Any) -> Optional[date]:
        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            try:
                # يدعم "2026-03-27"
                return date.fromisoformat(value)
            except ValueError:
                try:
                    # يدعم "2026-03-27T10:30:00"
                    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                except ValueError:
                    return None

        return None

    @staticmethod
    def createDevice(row: Dict[str, Any]) -> Device:
        """
        Create a device object from a database row.

        Expected keys in row:
        - device_id
        - device_name
        - device_type
        - installation_date
        - user_id
        - is_shiftable (optional)
        - power_rating (optional)
        - consumption_kwh (optional)
        - production_kwh (optional)
        """

        device_id = row["device_id"]
        device_name = row.get("device_name", "Unknown Device")
        device_type = row.get("device_type", "")
        installation_date = DeviceFactory._parse_installation_date(
            row.get("installation_date")
        )
        user_id = str(row["user_id"])

        if device_type == "consumption":
            return consumptionDevice(
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                installation_date=installation_date,
                user_id=user_id,
                consumption_kwh=float(row.get("consumption_kwh", 0.0) or 0.0),
                power_rating=float(row.get("power_rating", 0.0) or 0.0),
            )

        if device_type == "production":
            return productionDevice(
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                installation_date=installation_date,
                user_id=user_id,
                production_kwh=float(row.get("production_kwh", 0.0) or 0.0),
            )

        return Device(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            installation_date=installation_date,
            user_id=user_id,
        )