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
            self.supabase.table("users")
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

        result = self.supabase.table("users").insert(row).execute()

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
            self.supabase.table("users")
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
            self.supabase.table("users")
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
            self.supabase.table("users")
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
            self.supabase.table("energycalculation")
            .select("*")
            .eq("user_id", str(user_id))
            .gte("date", cycle_start.isoformat())
            .lte("date", cycle_end.isoformat())
            .order("date", desc=False)
            .execute()
        )

        return getattr(result, "data", None) or []

    # ── Sprint 2: Stats chart ──────────────────────────────────────
    # Added for the Home screen statistics chart (Week/Month/Year).
    # Fetches only the columns needed for chart rendering.
    # Separate from get_current_cycle_energy_rows() to avoid coupling
    # stats queries to the billing cycle logic.

    def get_energy_rows_for_range(
        self,
        user_id: str,
        start: DateType,
        end: DateType,
    ) -> List[Dict[str, Any]]:
        """
        Fetch energycalculation rows for a user within an arbitrary date range.

        Returns only: date, solar_production, total_consumption.
        Used by StatsService to build the statistics chart.
        """
        result = (
            self.supabase.table("energycalculation")
            .select("date, solar_production, total_consumption")
            .eq("user_id", str(user_id))
            .gte("date", start.isoformat())
            .lte("date", end.isoformat())
            .order("date", desc=False)
            .execute()
        )
        return getattr(result, "data", None) or []

    # ── End Sprint 2: Stats chart ──────────────────────────────────

    def get_users_with_energy(self) -> List[str]:
        """
        Get all users who have energy data.

        Used by:
        - scheduler jobs
        """

        result = self.supabase.table("energycalculation").select("user_id").execute()

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
            self.supabase.table("billprediction")
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
            self.supabase.table("billprediction")
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
                self.supabase.table("billprediction")
                .update(payload)
                .eq("limit_id", limit_id)
                .execute()
            )

            return limit_id

        # ---- INSERT NEW ROW ----
        result = self.supabase.table("billprediction").insert(payload).execute()

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

    def get_devices_by_type(
        self, user_id: str, device_type: str
    ) -> List[Dict[str, Any]]:
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

    # =========================================================
    # REAL-TIME DEVICE UPDATE (new)
    # ---------------------------------------------------------
    # Updates the device table columns directly on every sensor
    # reading. No new rows — just UPDATE existing device row.
    # =========================================================

    def get_device_row(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get a single device row by device_id."""
        response = (
            self.supabase.table("device")
            .select(
                "device_id, device_type, consumption, production, total_energy, total_energy_daily, last_reading_at, is_on"
            )
            .eq("device_id", device_id)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def update_device_realtime(
        self,
        device_id: int,
        payload: Dict[str, Any],
    ) -> None:
        """
        UPDATE the device row with new real-time values.
        Called on every sensor reading.
        Payload contains: consumption/production, is_on,
        total_energy_daily, total_energy, last_reading_at
        """
        self.supabase.table("device").update(payload).eq(
            "device_id", device_id
        ).execute()

    def reset_all_daily_energy(self) -> None:
        """
        Reset total_energy_daily to 0 for ALL devices.
        Called by the midnight scheduler job every day.
        """
        self.supabase.table("device").update({"total_energy_daily": 0}).neq(
            "device_id", 0
        ).execute()

    def get_user_devices_realtime(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns all devices for a user with their live readings.
        Used by GET /realtime/{user_id}.
        """
        response = (
            self.supabase.table("device")
            .select(
                "device_id, device_name, device_type, consumption, production, is_on, total_energy_daily, total_energy, last_reading_at"
            )
            .eq("user_id", user_id)
            .order("device_id")
            .execute()
        )
        return response.data or []

    # =========================================================
    # ENERGY CALCULATION — Daily UPSERT (new)
    # ---------------------------------------------------------
    # Called every minute by the scheduler.
    # Reads total_energy_daily from device table for each user,
    # then UPSERT into energycalculation (one row per user per day).
    # =========================================================

    def get_all_user_ids(self) -> List[str]:
        """Get all distinct user_ids from the device table."""
        try:
            response = self.supabase.table("device").select("user_id").execute()
            rows = response.data or []
            return list(set(str(r["user_id"]) for r in rows if r.get("user_id")))
        except Exception:
            return []

    def get_user_daily_energy_totals(self, user_id: str) -> Dict[str, float]:
        """
        Sum total_energy_daily for all devices of a user.
        Returns: { "total_consumption": float, "solar_production": float }
        """
        try:
            response = (
                self.supabase.table("device")
                .select("device_type, total_energy_daily")
                .eq("user_id", user_id)
                .execute()
            )
            rows = response.data or []

            total_consumption = 0.0
            solar_production = 0.0

            for row in rows:
                kwh = float(row.get("total_energy_daily") or 0.0)
                if row.get("device_type") == "production":
                    solar_production += kwh
                else:
                    total_consumption += kwh

            return {
                "total_consumption": round(total_consumption, 6),
                "solar_production": round(solar_production, 6),
            }
        except Exception:
            return {"total_consumption": 0.0, "solar_production": 0.0}

    def upsert_energy_calculation(
        self,
        user_id: str,
        date_str: str,
        total_consumption: float,
        solar_production: float,
    ) -> None:
        """
        UPSERT into energycalculation.
        Uses manual check: if row exists → UPDATE, else → INSERT.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            payload = {
                "user_id": user_id,
                "date": date_str,
                "total_consumption": total_consumption,
                "solar_production": solar_production,
                "total_cost": round(total_consumption * 0.18, 4),
                "carbon_reduction": round(solar_production * 0.568, 6),
                "cost_savings": round(solar_production * 0.18, 4),
            }

            # Check if row exists for this user + date
            existing = (
                self.supabase.table("energycalculation")
                .select("calculation_id")
                .eq("user_id", user_id)
                .eq("date", date_str)
                .limit(1)
                .execute()
            )
            rows = existing.data or []

            if rows:
                # UPDATE existing row
                calc_id = rows[0]["calculation_id"]
                self.supabase.table("energycalculation").update(
                    {
                        "total_consumption": total_consumption,
                        "solar_production": solar_production,
                        "total_cost": round(total_consumption * 0.18, 4),
                        "carbon_reduction": round(solar_production * 0.568, 6),
                        "cost_savings": round(solar_production * 0.18, 4),
                    }
                ).eq("calculation_id", calc_id).execute()
            else:
                # INSERT new row
                self.supabase.table("energycalculation").insert(payload).execute()

        except Exception as e:
            logging.getLogger(__name__).error(
                f"upsert_energy_calculation failed for {user_id}: {e}"
            )

    # ═══════════════════════════════════════════════════════════════
    # SOLAR FORECAST — Sprint 2
    # ---------------------------------------------------------------
    # days_offline logic updated:
    #   1. Check energycalculation for today's solar_production
    #   2. If 0 or missing → get latest last_reading_at across ALL
    #      production devices for the user
    #   3. Use that timestamp to compute days_offline
    # ═══════════════════════════════════════════════════════════════

    def get_user_location(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Return location, latitude, longitude for a user.
        Used by SolarForecastService to determine city and GHI region.
        """
        rows = (
            self.supabase.table("users")
            .select("location, latitude, longitude")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ).data or []
        return rows[0] if rows else None

    def get_production_device(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the first production device for a user.
        Used to get panel_capacity and installation_date.
        Returns dict with: device_id, panel_capacity, installation_date.
        """
        rows = (
            self.supabase.table("device")
            .select("device_id, panel_capacity, installation_date")
            .eq("user_id", user_id)
            .eq("device_type", "production")
            .limit(1)
            .execute()
        ).data or []
        return rows[0] if rows else None

    def get_all_production_devices(self) -> List[Dict[str, Any]]:
        """
        Return all production devices across all users.
        Used by DeviceMonitor.run() for the daily check.
        Returns distinct user_ids with their devices.
        """
        return (
            self.supabase.table("device")
            .select("device_id, user_id, installation_date")
            .eq("device_type", "production")
            .execute()
        ).data or []

    def get_production_devices_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Return all production devices for a specific user.
        Used by DeviceMonitor.check_user().
        """
        return (
            self.supabase.table("device")
            .select("device_id, user_id, installation_date")
            .eq("user_id", user_id)
            .eq("device_type", "production")
            .execute()
        ).data or []

    def get_latest_production_reading(self, user_id: str) -> Optional[str]:
        """
        Return the most recent last_reading_at across ALL production
        devices for a user.

        Why across all devices:
          A user may have multiple solar panels. If one panel has a wiring
          issue, last_reading_at of other panels would still be recent.
          We use the LATEST reading across all devices — if even one device
          sent a reading today, days_offline = 0.
          The actual decision is based on last_reading_at, not is_on,
          because is_on can be True while a wiring issue causes 0 production.

        Returns ISO timestamp string, or None if no readings exist.
        """
        rows = (
            self.supabase.table("device")
            .select("last_reading_at")
            .eq("user_id", user_id)
            .eq("device_type", "production")
            .not_.is_("last_reading_at", "null")
            .order("last_reading_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
        return rows[0]["last_reading_at"] if rows else None

    def get_today_solar_production(
        self,
        user_id: str,
        today: "DateType",
    ) -> float:
        """
        Return today's solar_production from energycalculation.
        Returns 0.0 if no row exists for today.

        Used as the first check in DeviceMonitor:
          if solar_production == 0.0 today → possible device issue
          → proceed to check last_reading_at
        """
        rows = (
            self.supabase.table("energycalculation")
            .select("solar_production")
            .eq("user_id", user_id)
            .eq("date", today.isoformat())
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return 0.0
        return float(rows[0].get("solar_production") or 0.0)

    def get_season_energy_rows(
        self,
        user_id: str,
        start: "DateType",
        end: "DateType",
    ) -> List[Dict[str, Any]]:
        """
        Return energycalculation rows with solar_production > 0
        within a date range (inclusive).
        Used by SolarForecastService to count collected days.
        """
        return (
            self.supabase.table("energycalculation")
            .select("date, solar_production")
            .eq("user_id", user_id)
            .gte("date", start.isoformat())
            .lte("date", end.isoformat())
            .gt("solar_production", 0)
            .execute()
        ).data or []

    def check_notification_exists(
        self,
        user_id: str,
        notif_type: str,
        key: str,
    ) -> bool:
        """
        Check if a notification with the given dedup key already exists.
        Uses ilike() — avoids filtering on 'timestamp' (PostgreSQL reserved).
        See Change Log v4, Section 3.16.
        """
        try:
            res = (
                self.supabase.table("notification")
                .select("notification_type")
                .eq("user_id", user_id)
                .eq("notification_type", notif_type)
                .ilike("content", f"%{key}%")
                .limit(1)
                .execute()
            )
            return len(res.data or []) > 0
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════
# END SOLAR FORECAST — Sprint 2
# ═══════════════════════════════════════════════════════════════
