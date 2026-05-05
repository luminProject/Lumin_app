# lumin_backend/app/models/realtime_reading.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RealtimeReading:
    """
    RealtimeReading model.

    Holds state for one live sensor reading and contains the
    business logic for:
      - calculating elapsed time since last reading
      - converting Watts → kWh for the interval
      - determining is_on status
      - building the DB update payload

    Pattern: Router → Facade → Model → DatabaseManager
    """

    device_id:   int
    device_type: str
    watts:       float
    now:         datetime

    # State loaded from DB
    last_reading_at:    Optional[datetime] = None
    current_total_daily: float = 0.0
    current_total:       float = 0.0

    # Computed (set after process())
    elapsed_seconds: float = 5.0
    kwh_added:       float = 0.0
    is_on:           bool  = False

    # =========================================================
    # Factory
    # =========================================================

    @classmethod
    def fromDeviceRow(
        cls,
        device_row: Dict[str, Any],
        watts: float,
        reading_time_iso: str,
    ) -> "RealtimeReading":
        """
        Create a RealtimeReading from a raw device DB row + new reading.
        """
        now = datetime.fromisoformat(
            reading_time_iso.replace("Z", "+00:00")
        )

        # Parse last_reading_at
        last_reading_at = None
        raw_last = device_row.get("last_reading_at")
        if raw_last:
            try:
                last_reading_at = datetime.fromisoformat(
                    str(raw_last).replace("Z", "+00:00")
                )
            except Exception:
                last_reading_at = None

        return cls(
            device_id=device_row["device_id"],
            device_type=device_row.get("device_type", "consumption"),
            watts=watts,
            now=now,
            last_reading_at=last_reading_at,
            current_total_daily=float(device_row.get("total_energy_daily") or 0.0),
            current_total=float(device_row.get("total_energy") or 0.0),
        )

    # =========================================================
    # Business Logic
    # =========================================================

    def process(self) -> None:
        """
        Run all calculations:
        1. Calculate elapsed seconds since last reading
        2. Convert watts → kWh for the interval
        3. Determine is_on
        """
        self.elapsed_seconds = self._calculate_elapsed()
        self.kwh_added       = self._watts_to_kwh(self.watts, self.elapsed_seconds)
        self.is_on           = self.watts > 1.0

    def _calculate_elapsed(self) -> float:
        """
        Calculate elapsed seconds since last reading.
        Clamps to 5s default if no previous reading or out of range.
        """
        if self.last_reading_at is None:
            return 5.0

        try:
            elapsed = (self.now - self.last_reading_at).total_seconds()
            # Clamp: default 5s if negative or unreasonably large (>60s)
            if elapsed <= 0 or elapsed > 60:
                return 5.0
            return elapsed
        except Exception:
            return 5.0

    def _watts_to_kwh(self, watts: float, seconds: float) -> float:
        """
        Convert power (W) over a time interval to energy (kWh).
        Formula: kWh = (W × s) ÷ 3,600,000
        """
        return (watts * seconds) / 3_600_000.0

    # =========================================================
    # Serialization
    # =========================================================

    def build_db_payload(self) -> Dict[str, Any]:
        """
        Build the payload for updating the device row in the DB.
        Called by the Facade to pass to DatabaseManager.
        """
        payload: Dict[str, Any] = {
            "is_on":              self.is_on,
            "last_reading_at":    self.now.isoformat(),
            "total_energy_daily": round(self.current_total_daily + self.kwh_added, 6),
            "total_energy":       round(self.current_total + self.kwh_added, 6),
        }

        if self.device_type == "consumption":
            payload["consumption"] = round(self.watts, 2)
        else:
            payload["production"] = round(self.watts, 2)

        return payload

    def to_response_dict(self) -> Dict[str, Any]:
        """Build a response dict for the API."""
        payload = self.build_db_payload()
        return {
            "success":      True,
            "device_id":    self.device_id,
            "device_type":  self.device_type,
            "watts":        round(self.watts, 2),
            "is_on":        self.is_on,
            "kwh_added":    round(self.kwh_added, 6),
            "total_daily":  payload["total_energy_daily"],
            "total_energy": payload["total_energy"],
        }


# ─── Home Page Aggregation ───────────────────────────────────

class RealtimeSummary:
    """
    Aggregates per-device realtime data into Home page summary.

    Uses total_energy_daily (cumulative kWh today) for the main values,
    and instant watts (consumption/production) only for per-device display.
    """

    def __init__(self, device_rows: List[Dict[str, Any]]):
        self.device_rows = device_rows
        self.solar_kwh       = 0.0
        self.consumption_kwh = 0.0
        self.grid_kwh        = 0.0

    def compute(self) -> None:
        """Sum up total_energy_daily per device type."""
        for row in self.device_rows:
            daily = float(row.get("total_energy_daily") or 0.0)
            if row.get("device_type") == "production":
                self.solar_kwh += daily
            else:
                self.consumption_kwh += daily

        # Grid = how much we needed from the grid today
        self.grid_kwh = max(0.0, self.consumption_kwh - self.solar_kwh)

    def to_response_dict(self) -> Dict[str, Any]:
        return {
            "success": True,
            "status":  "success",
            "code":    "REALTIME_FETCHED",
            "message": "Real-time data fetched successfully.",
            "data": {
                "solar_production_kwh":  round(self.solar_kwh, 4),
                "total_consumption_kwh": round(self.consumption_kwh, 4),
                "grid_kwh":              round(self.grid_kwh, 4),
                "devices":               self.device_rows,
            },
        }