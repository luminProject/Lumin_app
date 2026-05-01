# lumin_backend/app/models/recommendation.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Recommendation:
    """
    Recommendation model.
    Holds state (id, text, timestamp, user_id, device_id) and contains
    the business logic for building solar/general recommendations.
    """

    recommendation_id: Optional[int] = None
    recommendation_text: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = ""
    device_id: Optional[int] = None

    # Internal generation state
    _best_period: Optional[str] = None
    _best_period_avg: float = 0.0
    _period_averages: Dict[str, float] = field(default_factory=dict)
    _matched_device: Optional[Dict[str, Any]] = None

    # Period constants
    PERIOD_MORNING = "morning"
    PERIOD_MIDDAY = "midday"
    PERIOD_AFTERNOON = "afternoon"
    PERIOD_NIGHT = "night"

    # =========================================================
    # Original placeholder methods (kept for compatibility)
    # =========================================================

    def generateRecommendation(self, consumptionHistory: float) -> str:
        return self.recommendation_text

    def sendRecommendation(self) -> str:
        return self.recommendation_text

    def getData(self) -> float:
        return 0.0

    def update(self) -> None:
        return None

    # =========================================================
    # Solar Recommendation Logic
    # =========================================================

    def buildSolarFromReadings(
        self,
        solar_rows: List[Dict[str, Any]],
        shiftable_devices: List[Dict[str, Any]],
        device_readings_by_id: Dict[int, List[Dict[str, Any]]],
    ) -> bool:
        """
        Build a solar recommendation from raw sensor readings.
        Returns True if successful, False if data is insufficient.
        """
        avg_by_period = self._average_kwh_by_period(solar_rows)
        if not avg_by_period:
            return False

        best_period, best_avg = self._find_best_period(avg_by_period)
        if best_period is None:
            return False

        self._best_period = best_period
        self._best_period_avg = best_avg
        self._period_averages = avg_by_period

        matched = None
        if shiftable_devices:
            matched = self._choose_closest_device(
                devices=shiftable_devices,
                target_period=best_period,
                target_kwh=best_avg,
                device_readings_by_id=device_readings_by_id,
            )

        self._matched_device = matched
        if matched:
            self.device_id = matched["device_id"]

        self.recommendation_text = self._build_text(best_period, matched)
        return True

    def buildFromGeneralText(self, general_text: str) -> None:
        """Set the recommendation text from a general (DB-stored) tip."""
        self.recommendation_text = general_text
        self.device_id = None

    # =========================================================
    # User Profile Helper
    # =========================================================

    @staticmethod
    def userHasSolar(profile: Optional[Dict[str, Any]]) -> bool:
        """Check if a user profile indicates solar panels."""
        if not profile:
            return False
        has_solar_panels = profile.get("has_solar_panels")
        energy_source = profile.get("energy_source", "")
        return bool(has_solar_panels) and "solar" in (energy_source or "").lower()

    # =========================================================
    # Period Helpers
    # =========================================================

    def _parse_timestamp(self, value: str) -> datetime:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)

    def _get_period(self, dt: datetime) -> str:
        hour = dt.hour
        if 6 <= hour < 10:
            return self.PERIOD_MORNING
        if 10 <= hour < 14:
            return self.PERIOD_MIDDAY
        if 14 <= hour < 18:
            return self.PERIOD_AFTERNOON
        return self.PERIOD_NIGHT

    def _average_kwh_by_period(self, rows: List[Dict[str, Any]]) -> Dict[str, float]:
        grouped: Dict[str, List[float]] = defaultdict(list)

        for row in rows:
            reading_time = row.get("reading_time")
            kwh_value = row.get("kwh_value")
            if reading_time is None or kwh_value is None:
                continue
            try:
                ts = self._parse_timestamp(reading_time)
                kwh = float(kwh_value)
            except (ValueError, TypeError):
                continue
            period = self._get_period(ts)
            grouped[period].append(kwh)

        averages: Dict[str, float] = {}
        for period, values in grouped.items():
            if values:
                averages[period] = sum(values) / len(values)
        return averages

    def _find_best_period(
        self, averages: Dict[str, float]
    ) -> Tuple[Optional[str], float]:
        if not averages:
            return None, 0.0
        best_period = max(averages, key=averages.get)
        return best_period, averages[best_period]

    def _calculate_device_avg_in_period(
        self,
        rows: List[Dict[str, Any]],
        target_period: str,
    ) -> Optional[float]:
        if not rows:
            return None

        values: List[float] = []
        for row in rows:
            reading_time = row.get("reading_time")
            kwh_value = row.get("kwh_value")
            if reading_time is None or kwh_value is None:
                continue
            try:
                ts = self._parse_timestamp(reading_time)
                kwh = float(kwh_value)
            except (ValueError, TypeError):
                continue
            if self._get_period(ts) == target_period:
                values.append(kwh)

        return sum(values) / len(values) if values else None

    def _choose_closest_device(
        self,
        devices: List[Dict[str, Any]],
        target_period: str,
        target_kwh: float,
        device_readings_by_id: Dict[int, List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        best_match: Optional[Dict[str, Any]] = None
        smallest_diff = float("inf")

        for device in devices:
            device_id = device.get("device_id")
            if device_id is None:
                continue

            rows = device_readings_by_id.get(device_id, [])
            avg_consumption = self._calculate_device_avg_in_period(rows, target_period)
            if avg_consumption is None:
                continue

            diff = abs(target_kwh - avg_consumption)
            candidate = {
                "device_id": device_id,
                "device_name": device.get("device_name", "Unknown Device"),
                "device_type": device.get("device_type"),
                "is_shiftable": device.get("is_shiftable"),
                "avg_consumption": round(avg_consumption, 4),
                "target_production": round(target_kwh, 4),
                "difference": round(diff, 4),
                "recommended_period": target_period,
            }

            if diff < smallest_diff:
                smallest_diff = diff
                best_match = candidate

        return best_match

    def _build_text(
        self,
        best_period: str,
        matched_device: Optional[Dict[str, Any]],
    ) -> str:
        period_labels = {
            "morning":   "the morning (6 AM – 10 AM)",
            "midday":    "midday (10 AM – 2 PM)",
            "afternoon": "the afternoon (2 PM – 6 PM)",
            "night":     "the evening",
        }
        period_display = period_labels.get(best_period, best_period)

        if not matched_device:
            return (
                f"Your solar panels produce the most energy during {period_display}. "
                f"Try running your heavy appliances during this time to make the most of your solar energy."
            )

        device_name = matched_device["device_name"]
        return (
            f"Run your {device_name} during {period_display} — "
            f"that's when your solar panels are at their peak. "
            f"You'll save energy and reduce your electricity bill!"
        )

    # =========================================================
    # Serialization
    # =========================================================

    def build_db_payload(self) -> Dict[str, Any]:
        """Build the payload for inserting into the recommendation table."""
        return {
            "user_id": self.user_id,
            "recommendation_text": self.recommendation_text,
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
        }

    def to_response_dict(self) -> Dict[str, Any]:
        """Build a detailed response dict (for solar recommendations)."""
        return {
            "best_period": self._best_period,
            "best_period_avg_production": (
                round(self._best_period_avg, 4) if self._best_period_avg else None
            ),
            "period_averages": {
                k: round(v, 4) for k, v in self._period_averages.items()
            },
            "matched_device": self._matched_device,
        }