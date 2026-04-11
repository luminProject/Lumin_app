from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.models.recommendation import Recommendation


class RecommendationService:
    """
    Recommendation flow:

    For users with solar panels (has_solar_panels=True, energy_source='Grid + Solar'):
        1) Run solar-based logic (best period + shiftable device)
        2) Also pick one random general recommendation
        3) Save both to the recommendation table

    For users without solar panels (Grid only):
        1) Pick one random general recommendation
        2) Save it to the recommendation table
    """

    PERIOD_MORNING = "morning"
    PERIOD_MIDDAY = "midday"
    PERIOD_AFTERNOON = "afternoon"
    PERIOD_NIGHT = "night"

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    # =========================================================
    # Public Methods
    # =========================================================

    def generate_for_user(self, user_id: str) -> Dict[str, Any]:
        # 0) Check daily limit — max 2 recommendations per day
        if self._daily_limit_reached(user_id):
            return {
                "success": False,
                "status": "skipped",
                "code": "DAILY_LIMIT_REACHED",
                "message": "Daily recommendation limit (2) already reached for this user.",
                "user_id": user_id,
                "recommendation": None,
            }

        # 1) Get user profile to check energy_source / has_solar_panels
        user_profile = self._get_user_profile(user_id)
        has_solar = self._user_has_solar(user_profile)

        if has_solar:
            return self._generate_solar_recommendation(user_id)
        else:
            return self._generate_general_recommendation(user_id)

    def get_latest_recommendation(self, user_id: str) -> Dict[str, Any]:
        response = (
            self.supabase.table("recommendation")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data or []

        if not data:
            return {
                "success": False,
                "status": "empty",
                "code": "NO_RECOMMENDATIONS",
                "message": "No recommendations found for this user.",
                "data": None,
            }

        return {
            "success": True,
            "status": "success",
            "code": "LATEST_RECOMMENDATION_FETCHED",
            "message": "Latest recommendation fetched successfully.",
            "data": data[0],
        }

    def get_all_recommendations(self, user_id: str) -> Dict[str, Any]:
        response = (
            self.supabase.table("recommendation")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .execute()
        )

        return {
            "success": True,
            "status": "success",
            "code": "RECOMMENDATIONS_FETCHED",
            "message": "Recommendations fetched successfully.",
            "data": response.data or [],
        }

    # =========================================================
    # Solar Recommendation (Grid + Solar users)
    # =========================================================

    def _generate_solar_recommendation(self, user_id: str) -> Dict[str, Any]:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)

        # 1) Get production devices
        production_devices = self._get_devices_by_type(
            user_id=user_id,
            device_type="production",
        )

        if not production_devices:
            # Solar user but no production devices → fall back to general
            return self._generate_general_recommendation(
                user_id=user_id,
                fallback_reason="NO_PRODUCTION_DEVICES",
            )

        production_device_ids = [d["device_id"] for d in production_devices]

        # 2) Get solar readings for last 7 days
        solar_rows = self._get_sensor_rows_for_devices(
            device_ids=production_device_ids,
            start_date=start_date,
            end_date=end_date,
        )

        if not solar_rows:
            return self._generate_general_recommendation(
                user_id=user_id,
                fallback_reason="NO_SOLAR_READINGS",
            )

        # 3) Average production by period
        avg_production_by_period = self._average_kwh_by_period(solar_rows)

        if not avg_production_by_period:
            return self._generate_general_recommendation(
                user_id=user_id,
                fallback_reason="NO_VALID_SOLAR_PERIODS",
            )

        # 4) Best period
        best_period, best_period_avg = self._find_best_period(avg_production_by_period)

        if best_period is None:
            return self._generate_general_recommendation(
                user_id=user_id,
                fallback_reason="BEST_PERIOD_NOT_FOUND",
            )

        # 5) Shiftable devices
        shiftable_devices = self._get_shiftable_consumption_devices(user_id)

        # 6) Choose best matching device
        matched_device = None
        if shiftable_devices:
            matched_device = self._choose_closest_device(
                devices=shiftable_devices,
                target_period=best_period,
                target_kwh=best_period_avg,
                start_date=start_date,
                end_date=end_date,
            )

        # 7) Build solar recommendation text
        solar_text = self._build_recommendation_text(
            best_period=best_period,
            best_period_avg_production=best_period_avg,
            matched_device=matched_device,
        )

        # 8) Pick a general recommendation and combine
        general_text = self._get_random_general_text()
        final_text = solar_text
        if general_text:
            final_text = f"{solar_text} Additionally: {general_text}"

        # 9) Save
        saved = self._save_recommendation(
            user_id=user_id,
            recommendation_text=final_text,
            device_id=matched_device["device_id"] if matched_device else None,
        )

        return {
            "success": True,
            "status": "success",
            "code": "RECOMMENDATION_GENERATED",
            "message": "Recommendation generated successfully.",
            "user_id": user_id,
            "user_type": "solar",
            "window_days": 7,
            "best_period": best_period,
            "best_period_avg_production": round(best_period_avg, 4),
            "period_averages": self._round_dict_values(avg_production_by_period),
            "matched_device": matched_device,
            "recommendation": saved,
        }

    # =========================================================
    # General Recommendation (Grid only users OR solar fallback)
    # =========================================================

    def _generate_general_recommendation(
        self,
        user_id: str,
        fallback_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        general_text = self._get_random_general_text()

        if not general_text:
            return {
                "success": False,
                "status": "empty",
                "code": "NO_GENERAL_RECOMMENDATIONS",
                "message": "No general recommendations found in the database.",
                "user_id": user_id,
                "user_type": "grid_only",
                "recommendation": None,
            }

        saved = self._save_recommendation(
            user_id=user_id,
            recommendation_text=general_text,
            device_id=None,
        )

        return {
            "success": True,
            "status": "success",
            "code": "GENERAL_RECOMMENDATION_GENERATED",
            "message": "General recommendation generated successfully.",
            "user_id": user_id,
            "user_type": "grid_only",
            "fallback_reason": fallback_reason,
            "recommendation": saved,
        }

    # =========================================================
    # General Recommendations Table Helpers
    # =========================================================

    def _get_random_general_text(self) -> Optional[str]:
        """Fetch all general recommendations and pick one at random."""
        try:
            response = (
                self.supabase.table("general_recommendations")
                .select("recommendation_text")
                .execute()
            )
            rows = response.data or []
            if not rows:
                return None
            chosen = random.choice(rows)
            return chosen.get("recommendation_text")
        except Exception:
            return None

    # =========================================================
    # Daily Limit Check
    # =========================================================

    def _daily_limit_reached(self, user_id: str, max_per_day: int = 2) -> bool:
        """Returns True if the user already received max_per_day recommendations today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        try:
            response = (
                self.supabase.table("recommendation")
                .select("recommendation_id")
                .eq("user_id", user_id)
                .gte("timestamp", today_start.isoformat())
                .execute()
            )
            count = len(response.data or [])
            return count >= max_per_day
        except Exception:
            return False  # If check fails, allow generation

    # =========================================================
    # User Profile Helpers
    # =========================================================

    def _get_user_profile(self, user_id: str) -> Optional[dict]:
        try:
            response = (
                self.supabase.table("users")
                .select("has_solar_panels, energy_source")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            data = response.data or []
            return data[0] if data else None
        except Exception:
            return None

    def _user_has_solar(self, profile: Optional[dict]) -> bool:
        if not profile:
            return False
        has_solar_panels = profile.get("has_solar_panels")
        energy_source = profile.get("energy_source", "")
        # True only if explicitly has solar panels AND energy source includes Solar
        return bool(has_solar_panels) and "solar" in (energy_source or "").lower()

    # =========================================================
    # Database Helpers
    # =========================================================

    def _get_devices_by_type(self, user_id: str, device_type: str) -> List[dict]:
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .eq("device_type", device_type)
            .execute()
        )
        return response.data or []

    def _get_shiftable_consumption_devices(self, user_id: str) -> List[dict]:
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .eq("device_type", "consumption")
            .eq("is_shiftable", True)
            .execute()
        )
        return response.data or []

    def _get_sensor_rows_for_devices(
        self,
        device_ids: List[int],
        start_date: datetime,
        end_date: datetime,
    ) -> List[dict]:
        if not device_ids:
            return []

        response = (
            self.supabase.table("sensor_data")
            .select("device_id, reading_time, kwh_value")
            .in_("device_id", device_ids)
            .gte("reading_time", start_date.isoformat())
            .lte("reading_time", end_date.isoformat())
            .order("reading_time")
            .execute()
        )
        return response.data or []

    def _save_recommendation(
        self,
        user_id: str,
        recommendation_text: str,
        device_id: Optional[int],
    ) -> dict:
        recommendation = Recommendation(
            recommendation_id=None,
            recommendation_text=recommendation_text,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            device_id=device_id,
        )

        payload = {
            "user_id": recommendation.user_id,
            "recommendation_text": recommendation.recommendation_text,
            "timestamp": recommendation.timestamp.isoformat(),
            "device_id": recommendation.device_id,
        }

        response = self.supabase.table("recommendation").insert(payload).execute()

        if response.data:
            return response.data[0]

        return payload

    # =========================================================
    # Core Logic Helpers
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

    def _average_kwh_by_period(self, rows: List[dict]) -> Dict[str, float]:
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

    def _calculate_device_avg_consumption_in_period(
        self,
        device_id: int,
        target_period: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[float]:
        rows = self._get_sensor_rows_for_devices(
            device_ids=[device_id],
            start_date=start_date,
            end_date=end_date,
        )

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
        devices: List[dict],
        target_period: str,
        target_kwh: float,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[dict]:
        best_match: Optional[dict] = None
        smallest_difference = float("inf")

        for device in devices:
            device_id = device.get("device_id")
            if device_id is None:
                continue

            avg_consumption = self._calculate_device_avg_consumption_in_period(
                device_id=device_id,
                target_period=target_period,
                start_date=start_date,
                end_date=end_date,
            )

            if avg_consumption is None:
                continue

            difference = abs(target_kwh - avg_consumption)

            candidate = {
                "device_id": device_id,
                "device_name": device.get("device_name", "Unknown Device"),
                "device_type": device.get("device_type"),
                "is_shiftable": device.get("is_shiftable"),
                "avg_consumption": round(avg_consumption, 4),
                "target_production": round(target_kwh, 4),
                "difference": round(difference, 4),
                "recommended_period": target_period,
            }

            if difference < smallest_difference:
                smallest_difference = difference
                best_match = candidate

        return best_match

    def _build_recommendation_text(
        self,
        best_period: str,
        best_period_avg_production: float,
        matched_device: Optional[dict],
    ) -> str:
        if not matched_device:
            return (
                f"The best solar production period is {best_period}, "
                f"with an average production of {best_period_avg_production:.2f} kWh. "
                f"No suitable shiftable device with enough readings was found."
            )

        return (
            f"The best time to run {matched_device['device_name']} is during the {best_period}. "
            f"Average solar production in this period is {best_period_avg_production:.2f} kWh, "
            f"and the device average consumption is {matched_device['avg_consumption']:.2f} kWh."
        )

    # =========================================================
    # Response Helpers
    # =========================================================

    def _build_empty_response(
        self,
        code: str,
        message: str,
        user_id: str,
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "empty",
            "code": code,
            "message": message,
            "user_id": user_id,
            "window_days": 7,
            "best_period": None,
            "best_period_avg_production": None,
            "period_averages": {},
            "matched_device": None,
            "recommendation": None,
        }

    def _round_dict_values(self, data: Dict[str, float]) -> Dict[str, float]:
        return {key: round(value, 4) for key, value in data.items()}