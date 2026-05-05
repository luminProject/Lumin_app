"""
app/tasks/device_monitor.py

Daily Device Monitor — checks production devices for missing data
and sends notifications via DatabaseManager (DB insert) + FCMService (push).

Responsibilities:
  - Run daily at 08:00 Saudi time via APScheduler (scheduler.py)
  - Triggered manually via POST /dev/trigger-monitor/{user_id} (testing only)
  - Called automatically on every GET /solar-forecast/{user_id} request

Notification types managed here:
  - device_warning   : sent every day the device has no data (days 1–14)
  - feature_disabled : sent once per offline cycle (resets on reconnect)

Dedup strategy:
  Both notification types embed a unique key inside the content string.
  Dedup is checked via ilike() on the content field instead of filtering
  by timestamp — this avoids PostgreSQL reserved-word conflicts with the
  `timestamp` column name in the Supabase Python client.

  device_warning   → content ends with  #warn_YYYYMMDD
  feature_disabled → content ends with  #offline_since_YYYYMMDD

  The offline key is built from last_reading_date, so it automatically
  resets when the user reconnects (last_reading_date changes).
"""

import os
import logging
from datetime import date, datetime, timezone
from typing import Optional
from dotenv import load_dotenv
import supabase as supabase_

from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService
from app.models.solar_forecast_service import SolarForecastService
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("device_monitor")


# ═══════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════

# Number of consecutive offline days before Solar Forecast is paused
FEATURE_DISABLE_DAYS = 15

NOTIF_DEVICE_WARNING   = "device_warning"
NOTIF_FEATURE_DISABLED = "feature_disabled"

# FCM push titles per notification type
_PUSH_TITLES = {
    NOTIF_DEVICE_WARNING:   "⚠️ No Solar Data Today",
    NOTIF_FEATURE_DISABLED: "🚫 Solar Forecast Paused",
}


# ═══════════════════════════════════════════════
#  MONITOR CLASS
# ═══════════════════════════════════════════════

class DeviceMonitor:
    """
    Monitors production devices for missing sensor data and sends
    appropriate notifications via DatabaseManager + FCMService.

    Design note:
      DeviceMonitor is not part of the original class diagram.
      It was introduced in Sprint 2 as a background task to handle
      device failure scenarios defined in Change Log v3, Section 3.5.
      It reads from sensor_data and device tables — no new DB tables required.
    """

    def __init__(self, supabase_client):
        self.db = DatabaseManager(supabase_client)
        # Keep raw client for queries not covered by DatabaseManager
        self._supabase = supabase_client

    # ─────────────────────────────────────────
    #  PUBLIC: run for all production devices
    #  Called by APScheduler at 08:00 Saudi time
    # ─────────────────────────────────────────
    def run(self):
        """Check all production devices across all users."""
        today = date.today()
        logger.info(f"[DeviceMonitor] Starting daily check — {today}")

        devices = (
            self._supabase.table("device")
            .select("device_id, user_id, installation_date")
            .eq("device_type", "production")
            .execute()
        ).data

        logger.info(f"[DeviceMonitor] Found {len(devices)} production device(s)")

        for device in devices:
            try:
                self._check_device(device, today)
            except Exception as e:
                logger.error(
                    f"[DeviceMonitor] Error for device {device['device_id']}: {e}"
                )

        logger.info("[DeviceMonitor] Daily check complete")

    # ─────────────────────────────────────────
    #  PUBLIC: run for a single user
    #  Used by: /dev/trigger-monitor (testing)
    #           GET /solar-forecast (automatic trigger on page open)
    # ─────────────────────────────────────────
    def check_user(self, user_id: str, test_date: str = None):
        """
        Check all production devices for one user.

        Parameters
        ----------
        user_id   : str  — target user UUID
        test_date : str  — optional ISO date string (YYYY-MM-DD) for testing.
                           When provided, overrides date.today().
        """
        today = date.fromisoformat(test_date) if test_date else date.today()

        devices = (
            self._supabase.table("device")
            .select("device_id, user_id, installation_date")
            .eq("user_id", user_id)
            .eq("device_type", "production")
            .execute()
        ).data

        logger.info(
            f"[DeviceMonitor] check_user({user_id}) today={today}"
            f" — {len(devices)} device(s)"
        )

        for device in devices:
            self._check_device(device, today)

    # ─────────────────────────────────────────
    #  PRIVATE: check a single device
    # ─────────────────────────────────────────
    def _check_device(self, device: dict, today: date):
        """
        Core logic for one device:
          1. Find last sensor reading date
          2. Compute days offline
          3. Send device_warning (daily, days 1–14)
             OR feature_disabled (once per offline cycle, day 15+)
        """
        device_id         = device["device_id"]
        user_id           = device["user_id"]
        installation_date = date.fromisoformat(device["installation_date"])

        logger.info(f"  → device_id={device_id} user_id={user_id}")

        # ── 1. Fetch last sensor reading ─────────────────────────────
        last_readings = (
            self._supabase.table("sensor_data")
            .select("reading_time")
            .eq("device_id", device_id)
            .order("reading_time", desc=True)
            .limit(1)
            .execute()
        ).data

        last_reading_date: Optional[date] = None
        if last_readings:
            # Strip timezone suffix before parsing
            last_reading_date = datetime.fromisoformat(
                str(last_readings[0]["reading_time"])
                .split("+")[0]
                .split("Z")[0]
            ).date()
            days_offline = max(0, (today - last_reading_date).days)
        else:
            days_offline = max(0, (today - installation_date).days)

        logger.info(
            f"    days_offline={days_offline}"
            f" (last_reading={last_reading_date}, today={today})"
        )

        # ── 2. Device is online today — nothing to do ─────────────────
        if days_offline == 0:
            logger.info(f"    ✓ Device online — OK")
            return

        # ── 3. Feature disabled (15+ days offline) ───────────────────
        if days_offline >= FEATURE_DISABLE_DAYS:
            # Key built from last_reading_date — resets on reconnect
            offline_key  = (
                f"#offline_since_"
                f"{last_reading_date.strftime('%Y%m%d') if last_reading_date else '00000000'}"
            )
            already_sent = self._content_key_exists(
                user_id, NOTIF_FEATURE_DISABLED, offline_key
            )

            logger.info(
                f"    feature_disabled check:"
                f" key={offline_key} already_sent={already_sent}"
            )

            if not already_sent:
                content = (
                    f"Solar Forecast has been paused. "
                    f"Your device has been offline for {days_offline} days. "
                    f"Reconnect to resume data collection. "
                    f"{offline_key}"
                )
                self._send_notification(user_id, NOTIF_FEATURE_DISABLED, content)
                logger.info(f"    🚫 Sent feature_disabled ({offline_key})")
            else:
                logger.info(f"    ℹ️  feature_disabled already sent for this cycle")
            return

        # ── 4. Device warning (days 1–14) — sent once per day ────────
        warn_key     = f"#warn_{today.strftime('%Y%m%d')}"
        already_sent = self._content_key_exists(
            user_id, NOTIF_DEVICE_WARNING, warn_key
        )

        logger.info(
            f"    device_warning check:"
            f" key={warn_key} already_sent={already_sent}"
        )

        if not already_sent:
            content = (
                f"No solar data received today ({today.strftime('%b %d, %Y')}). "
                f"We couldn't read your production device. "
                f"Check your connection. "
                f"Day {days_offline} of {FEATURE_DISABLE_DAYS} before forecast pauses. "
                f"{warn_key}"
            )
            self._send_notification(user_id, NOTIF_DEVICE_WARNING, content)
            logger.info(
                f"    ⚠️  Sent device_warning (day {days_offline}, {warn_key})"
            )
        else:
            logger.info(f"    ℹ️  device_warning already sent today")

    # ─────────────────────────────────────────
    #  PRIVATE: insert notification + FCM push
    # ─────────────────────────────────────────
    def _send_notification(
        self, user_id: str, notification_type: str, content: str
    ) -> None:
        """
        Insert a notification row via DatabaseManager and attempt FCM push.
        Push failure is caught silently — it must never block the DB write.
        """
        payload = {
            "user_id":           user_id,
            "notification_type": notification_type,
            "content":           content,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
        }
        self.db.insert_notification(payload)

        # FCM push (fail-safe)
        try:
            fcm_token = self.db.get_user_fcm_token(user_id)
            if fcm_token:
                FCMService.send_push(
                    fcm_token=fcm_token,
                    title=_PUSH_TITLES.get(notification_type, "🔔 Lumin"),
                    body=content[:100],
                )
        except Exception:
            pass

    # ─────────────────────────────────────────
    #  PRIVATE: content-based dedup check
    # ─────────────────────────────────────────
    def _content_key_exists(
        self, user_id: str, notif_type: str, key: str
    ) -> bool:
        """
        Check if a notification with the given key already exists
        by searching the content field with ilike().

        Why ilike and not timestamp filter:
          The `timestamp` column name is reserved in PostgreSQL.
          The Supabase Python client returns HTTP 400 when used as
          a filter directly. Content-based keys are a reliable workaround.
        """
        try:
            res = (
                self._supabase.table("notification")
                .select("notification_type")
                .eq("user_id", user_id)
                .eq("notification_type", notif_type)
                .ilike("content", f"%{key}%")
                .limit(1)
                .execute()
            )
            return len(res.data) > 0
        except Exception as e:
            logger.warning(f"    ⚠️  _content_key_exists error: {e}")
            # On error: return False so notification is sent (fail-safe)
            return False


# ═══════════════════════════════════════════════
#  ENTRY POINT (run as script)
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

    client = supabase_.create_client(SUPABASE_URL, SUPABASE_KEY)
    DeviceMonitor(client).run()