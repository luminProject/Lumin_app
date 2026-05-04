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

    # =============================
    # USER PROFILE
    # =============================

    def get_user_profile_row(self, user_id: str) -> Dict[str, Any] | None:
        """
        Read user profile row from users table.

        DatabaseManager returns raw dict only.
        It does not know the User model.
        """

        result = (
            self.supabase
            .table("users")
            .select("*")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        rows = getattr(result, "data", None) or []
        return rows[0] if rows else None

    def insert_user_profile_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert user profile row.
        """

        result = (
            self.supabase
            .table("users")
            .insert(row)
            .execute()
        )

        rows = getattr(result, "data", None) or []

        if not rows:
            raise ValueError("Failed to create profile")

        return rows[0]

    def update_user_profile_row(
        self,
        user_id: str,
        info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update user profile row.
        """

        (
            self.supabase
            .table("users")
            .update(info)
            .eq("user_id", str(user_id))
            .execute()
        )

        row = self.get_user_profile_row(user_id)

        if not row:
            raise ValueError("Profile not found")

        return row
    # =============================
    # USER BILLING DATE
    # =============================

    def get_user_last_billing_end_date(self, user_id: str) -> DateType | None:
        """
        Get last billing end date from users table.

        Used to:
        - Calculate current billing cycle
        - Define cycle_start = last_billing_end_date + 1
        """

        rows = (
            self.supabase
            .table("users")
            .select("last_billing_end_date")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        ).data or []

        if not rows:
            return None

        raw = rows[0].get("last_billing_end_date")
        if not raw:
            return None

        return DateType.fromisoformat(str(raw)[:10])


    def update_user_last_billing_end_date(
        self,
        user_id: str,
        last_billing_end_date: DateType,
    ) -> None:
        """
        Update billing end date.

        IMPORTANT:
        - This does NOT touch billprediction table.
        - System will react later when GET /bill is called.
        """

        (
            self.supabase
            .table("users")
            .update({"last_billing_end_date": last_billing_end_date.isoformat()})
            .eq("user_id", str(user_id))
            .execute()
        )


    # =============================
    # ENERGY DATA
    # =============================

    def get_current_cycle_energy_rows(
        self,
        user_id: str,
        cycle_start: DateType,
        cycle_end: DateType,
    ) -> List[Dict[str, Any]]:
        """
        Fetch energy rows within current billing cycle.

        Used for:
        - actual usage calculation
        - SMA-7 forecast
        """

        result = (
            self.supabase
            .table("energycalculation")
            .select("*")
            .eq("user_id", str(user_id))
            .gte("date", cycle_start.isoformat())
            .lte("date", cycle_end.isoformat())
            .order("date", desc=False)
            .execute()
        )

        return getattr(result, "data", None) or []


    def get_users_with_energy(self) -> List[str]:
        """
        Get all users who have energy data.

        Used by:
        - scheduler jobs
        """

        result = (
            self.supabase
            .table("energycalculation")
            .select("user_id")
            .execute()
        )

        rows = getattr(result, "data", None) or []
        return sorted(set(str(r["user_id"]) for r in rows if r.get("user_id")))


    # =============================
    # BILL PREDICTION TABLE
    # =============================

    def get_latest_bill_row(self, user_id: str) -> Dict[str, Any] | None:
        """
        Get latest bill row (by limit_id).

        Used ONLY for:
        - carrying forward limit_amount
        """

        rows = (
            self.supabase
            .table("billprediction")
            .select("*")
            .eq("user_id", str(user_id))
            .order("limit_id", desc=True)
            .limit(1)
            .execute()
        ).data or []

        return rows[0] if rows else None


    def get_bill_row_by_cycle(
        self,
        user_id: str,
        cycle_start: DateType,
    ) -> Dict[str, Any] | None:
        """
        Get bill row for a SPECIFIC cycle.

        IMPORTANT RULE:
        - cycle_start defines the identity of a billing cycle

        Used to decide:
        - update existing row
        - OR create new row
        """

        rows = (
            self.supabase
            .table("billprediction")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("cycle_start", cycle_start.isoformat())
            .limit(1)
            .execute()
        ).data or []

        return rows[0] if rows else None


    def save_current_cycle_bill(self, user_id: str, payload: Dict[str, Any]) -> int:
        """
        Save billprediction row for CURRENT cycle.

        Logic:
        1. Check if row exists for same user + cycle_start
        2. If yes → UPDATE
        3. If no  → INSERT new row
        """

        cycle_start = DateType.fromisoformat(str(payload["cycle_start"])[:10])

        current_row = self.get_bill_row_by_cycle(user_id, cycle_start)

        # ---- UPDATE EXISTING ROW ----
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

        # ---- INSERT NEW ROW ----
        result = (
            self.supabase
            .table("billprediction")
            .insert(payload)
            .execute()
        )

        data = getattr(result, "data", None) or []
        return int(data[0].get("limit_id") or 0) if data else 0
    
    
    





 # =========================================================
    # USERS (new)
    # ---------------------------------------------------------
    # NOTE: For reading the user profile, we reuse the existing
    # get_user_profile_row() method defined above (USER PROFILE
    # section) — no duplicate query is added here.
    #
    # The only NEW user-related method is get_user_fcm_token(),
    # required by the recommendation feature to send push
    # notifications via Firebase.
    # =========================================================

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