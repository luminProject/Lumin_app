from __future__ import annotations

from datetime import date as DateType
from typing import Any, Dict, List


class DatabaseManager:
    """
    Handles all database access related to monthly energy data
    and bill prediction data.
    """

    def __init__(self, supabase_client: Any):
        self.supabase = supabase_client

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