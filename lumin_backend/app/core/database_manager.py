from __future__ import annotations

from datetime import date as DateType, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import random


class DatabaseManager:
    """
    Handles all database access related to monthly energy data
    and bill prediction data.

    NOTE: This file follows the project's data-access pattern.
    All Supabase queries (select/insert/update) live here.
    """

    def __init__(self, supabase_client: Any):
        self.supabase = supabase_client

    # =========================================================
    # ENERGY (existing — DO NOT MODIFY)
    # =========================================================

    def get_current_month_energy_rows(self, user_id: str) -> List[Dict[str, Any]]:
        today = DateType.today()
        billing_month_start = today.replace(day=1).isoformat()

        if today.month == 12:
            next_month_start = DateType(today.year + 1, 1, 1).isoformat()
        else:
            next_month_start = DateType(today.year, today.month + 1, 1).isoformat()

        result = (
            self.supabase
            .table("energycalculation")
            .select("calculation_id, user_id, date, total_consumption, solar_production, total_cost")
            .eq("user_id", str(user_id))
            .gte("date", billing_month_start)
            .lt("date", next_month_start)
            .order("date", desc=False)
            .execute()
        )

        return getattr(result, "data", None) or []

    def get_users_with_current_month_energy(self) -> List[str]:
        today = DateType.today()
        billing_month_start = today.replace(day=1).isoformat()

        if today.month == 12:
            next_month_start = DateType(today.year + 1, 1, 1).isoformat()
        else:
            next_month_start = DateType(today.year, today.month + 1, 1).isoformat()

        result = (
            self.supabase
            .table("energycalculation")
            .select("user_id")
            .gte("date", billing_month_start)
            .lt("date", next_month_start)
            .execute()
        )

        rows = getattr(result, "data", None) or []
        user_ids: list[str] = []

        for row in rows:
            user_id = row.get("user_id")
            if user_id is not None:
                user_ids.append(str(user_id))

        return sorted(set(user_ids))

    # =========================================================
    # BILL (existing — DO NOT MODIFY)
    # =========================================================

    def get_current_month_bill_row(self, user_id: str) -> Dict[str, Any] | None:
        today = DateType.today()
        billing_month = today.replace(day=1).isoformat()

        rows = (
            self.supabase
            .table("billprediction")
            .select(
                "limit_id, user_id, limit_amount, actual_bill, predicted_bill, "
                "billing_month, current_usage_kwh, predicted_usage_kwh, "
                "forecast_available, days_passed, days_in_month, last_checkpoint_day"
            )
            .eq("user_id", str(user_id))
            .eq("billing_month", billing_month)
            .limit(1)
            .execute()
        ).data or []

        return rows[0] if rows else None

    def save_current_month_bill(self, user_id: str, payload: Dict[str, Any]) -> int:
        current_row = self.get_current_month_bill_row(user_id)

        if current_row:
            limit_id = int(current_row.get("limit_id") or 0)

            (
                self.supabase
                .table("billprediction")
                .update(payload)
                .eq("limit_id", limit_id)
                .execute()
            )

            return limit_id

        result = (
            self.supabase
            .table("billprediction")
            .insert(payload)
            .execute()
        )

        data = getattr(result, "data", None) or []
        if data:
            return int(data[0].get("limit_id") or 0)

        return 0

    # =========================================================
    # USERS (new)
    # ---------------------------------------------------------
    # These methods are required by the recommendation feature:
    #
    # 1) get_user_profile():
    #    The facade needs to know if a user owns solar panels
    #    so it can decide whether to generate a SOLAR-based
    #    recommendation (panels + shiftable devices logic) or
    #    a GENERAL recommendation (random tip from DB).
    #
    # 2) get_user_fcm_token():
    #    After saving a recommendation, the facade sends a push
    #    notification to the user's phone via Firebase. Firebase
    #    requires the device's FCM token, which is stored on the
    #    users table in the 'fcm_token' column.
    #
    # Both methods follow the project pattern: Supabase queries
    # belong ONLY here, not in the Facade or the Model.
    # =========================================================

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns the user's solar status (has_solar_panels + energy_source).
        Used by the facade to choose between Solar / General recommendation.
        """
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

    def get_user_fcm_token(self, user_id: str) -> Optional[str]:
        """
        Returns the user's FCM token (the unique ID of their phone for Firebase).
        Used by the facade to send push notifications via FCMService.
        """
        try:
            response = (
                self.supabase.table("users")
                .select("fcm_token")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            data = response.data or []
            return data[0].get("fcm_token") if data else None
        except Exception:
            return None

    # =========================================================
    # DEVICES (new — only what recommendation logic needs)
    # =========================================================

    def get_devices_by_type(self, user_id: str, device_type: str) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .eq("device_type", device_type)
            .execute()
        )
        return response.data or []

    def get_shiftable_consumption_devices(self, user_id: str) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .eq("device_type", "consumption")
            .eq("is_shiftable", True)
            .execute()
        )
        return response.data or []

    def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .order("device_id")
            .execute()
        )
        return response.data or []

    # =========================================================
    # SENSOR READINGS (new)
    # =========================================================

    def get_sensor_rows_for_devices(
        self,
        device_ids: List[int],
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
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

    # =========================================================
    # RECOMMENDATIONS (new)
    # =========================================================

    def insert_recommendation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.supabase.table("recommendation").insert(payload).execute()
        if response.data:
            return response.data[0]
        return payload

    def get_latest_recommendation(self, user_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self.supabase.table("recommendation")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def get_all_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("recommendation")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data or []

    def count_today_recommendations(self, user_id: str) -> int:
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
            return len(response.data or [])
        except Exception:
            return 0

    def count_week_solar_recommendations(self, user_id: str) -> int:
        week_start = datetime.now(timezone.utc) - timedelta(days=7)
        try:
            response = (
                self.supabase.table("recommendation")
                .select("recommendation_id")
                .eq("user_id", user_id)
                .not_.is_("device_id", "null")
                .gte("timestamp", week_start.isoformat())
                .execute()
            )
            return len(response.data or [])
        except Exception:
            return 0

    def get_random_general_recommendation_text(self) -> Optional[str]:
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
    # NOTIFICATIONS (new)
    # =========================================================

    def insert_notification(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        response = self.supabase.table("notification").insert(payload).execute()
        data = response.data or []
        return data[0] if data else None

    def get_user_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("notification")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data or []

    def get_latest_notification(self, user_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self.supabase.table("notification")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None