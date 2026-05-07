"""
app/tasks/device_monitor.py

Daily Device Monitor — checks production devices for missing data.
Sprint 2 Addition. See Change Log v4, Section 3.12.

Logic (per user, not per device):
  1. Get all distinct users who have production devices
  2. For each user: check today's solar_production in energycalculation
  3. If production = 0 or missing → get latest last_reading_at across
     ALL production devices for that user
  4. Use last_reading_at to compute days_offline and send notification
     (is_on is NOT used — wiring issues can cause is_on=True + zero production)

Notification:
  Uses Notification factories (forDeviceWarning, forFeatureDisabled) then
  DatabaseManager.insert_notification() + FCMService.send_push().
  See Change Log v4, Sections 3.15 and 3.16.
"""

import os
import logging
from datetime import date, datetime, timezone
from typing import Optional
from dotenv import load_dotenv
import supabase as supabase_

from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService
from app.models.notification import Notification

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("device_monitor")

FEATURE_DISABLE_DAYS = 15  # Must match solar_forecast_service.py


class DeviceMonitor:
    """
    Monitors solar production per user.
    All DB access through self.db (DatabaseManager).
    """

    def __init__(self, supabase_client):
        self.db = DatabaseManager(supabase_client)

    # ─────────────────────────────────────────
    #  PUBLIC: run for all users
    # ─────────────────────────────────────────
    def run(self):
        """Check all users who have production devices."""
        today = date.today()
        logger.info(f"[DeviceMonitor] Starting daily check — {today}")

        all_devices = self.db.get_all_production_devices()
        user_ids    = list({d["user_id"] for d in all_devices})

        logger.info(f"[DeviceMonitor] Found {len(user_ids)} user(s) with production devices")

        for user_id in user_ids:
            try:
                self._check_user_solar(user_id, today)
            except Exception as e:
                logger.error(f"[DeviceMonitor] Error for user {user_id}: {e}")

        logger.info("[DeviceMonitor] Daily check complete")

    # ─────────────────────────────────────────
    #  PUBLIC: run for a single user
    # ─────────────────────────────────────────
    def check_user(self, user_id: str, test_date: str = None):
        """Check a single user's solar production status."""
        today = date.fromisoformat(test_date) if test_date else date.today()
        logger.info(f"[DeviceMonitor] check_user({user_id}) today={today}")
        self._check_user_solar(user_id, today)

    # ─────────────────────────────────────────
    #  PRIVATE: check one user's solar status
    # ─────────────────────────────────────────
    def _check_user_solar(self, user_id: str, today: date):
        """
        Core logic per user:
          Step 1 — Check today's solar_production in energycalculation.
                   If production > 0 → device is working → nothing to do.
          Step 2 — If production = 0 or no row today:
                   Get latest last_reading_at across ALL production devices.
                   Use that timestamp to compute days_offline.
          Step 3 — Send device_warning (days 1–14) or
                   feature_disabled (day 15+) based on days_offline.

        is_on is NOT used for the offline decision.
        A wiring issue can cause is_on=True but zero production.
        last_reading_at is the reliable indicator.
        """
        logger.info(f"  → user_id={user_id}")

        # ── Step 1: today's production ────────────────────────────────
        today_production = self.db.get_today_solar_production(user_id, today)

        if today_production > 0:
            logger.info(
                f"    ✓ Solar production confirmed today ({today_production} kWh) — OK"
            )
            return

        # ── Step 2: latest last_reading_at across all panels ──────────
        raw_last = self.db.get_latest_production_reading(user_id)

        device = self.db.get_production_device(user_id)
        installation_date = today
        if device and device.get("installation_date"):
            installation_date = date.fromisoformat(
                str(device["installation_date"]).split("T")[0]
            )

        last_reading_date: Optional[date] = None
        if raw_last:
            last_reading_date = datetime.fromisoformat(
                str(raw_last).split("+")[0].split("Z")[0]
            ).date()
            days_offline = max(0, (today - last_reading_date).days)
        else:
            days_offline = max(0, (today - installation_date).days)

        logger.info(
            f"    production=0 today, days_offline={days_offline}"
            f" (last_reading={last_reading_date})"
        )

        if days_offline == 0:
            logger.info(
                "    ⚠ Zero production but device read today — possible intermittent issue"
            )
            return

        # ── Step 3: send notification ─────────────────────────────────
        if days_offline >= FEATURE_DISABLE_DAYS:
            last_str     = (
                last_reading_date.strftime("%Y%m%d")
                if last_reading_date else "00000000"
            )
            offline_key  = f"#offline_since_{last_str}"

            if not self.db.check_notification_exists(
                user_id, "feature_disabled", offline_key
            ):
                notif = Notification.forFeatureDisabled(
                    user_id=user_id,
                    days_offline=days_offline,
                    last_reading_date_str=last_str,
                )
                self._send(notif)
                logger.info(f"    🚫 Sent feature_disabled ({offline_key})")
            else:
                logger.info("    ℹ️  feature_disabled already sent for this cycle")
            return

        today_str = today.strftime("%Y%m%d")
        warn_key  = f"#warn_{today_str}"

        if not self.db.check_notification_exists(
            user_id, "device_warning", warn_key
        ):
            notif = Notification.forDeviceWarning(
                user_id=user_id,
                days_offline=days_offline,
                today_str=today_str,
                feature_disable_days=FEATURE_DISABLE_DAYS,
            )
            self._send(notif)
            logger.info(
                f"    ⚠️  Sent device_warning (day {days_offline}, {warn_key})"
            )
        else:
            logger.info("    ℹ️  device_warning already sent today")

    # ─────────────────────────────────────────
    #  PRIVATE: insert notification + FCM push
    # ─────────────────────────────────────────
    def _send(self, notif: Notification) -> None:
        """
        Insert notification row via DatabaseManager and attempt FCM push.
        Push failure is caught silently — must never block the DB write.
        """
        self.db.insert_notification(notif.build_db_payload())

        try:
            fcm_token = self.db.get_user_fcm_token(notif.user_id)
            if fcm_token:
                FCMService.send_push(
                    fcm_token=fcm_token,
                    title=notif.getPushTitle(),
                    body=notif.getPushBody(),
                )
        except Exception:
            pass


if __name__ == "__main__":
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    client = supabase_.create_client(SUPABASE_URL, SUPABASE_KEY)
    DeviceMonitor(client).run()