"""
scheduler.py

Runs automatic recommendation jobs based on user type:

For Solar users (Grid + Solar):
  - Saturday 3:00 PM Saudi time → Solar (custom) recommendation
  - Tuesday 7:00 PM Saudi time → General recommendation

For Grid-only users:
  - Monday 4:00 PM Saudi time → General recommendation
  - Thursday 8:00 PM Saudi time → General recommendation

Also runs Solar Forecast jobs daily (added by Solar Forecast feature):
  - 8:00 AM Saudi time (05:00 UTC) → Device Monitor (check offline devices)
  - 8:05 AM Saudi time (05:05 UTC) → Solar Forecast Check (sends forecast_ready if ready)

Saudi time = UTC+3
APScheduler day_of_week values: mon, tue, wed, thu, fri, sat, sun
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.supabase_client import supabase_admin
from app.core.lumin_facade import LuminFacade
from app.models.recommendation import Recommendation
from app.tasks.device_monitor import DeviceMonitor  # added by Solar Forecast feature
from app.models.solar_forecast_service import SolarForecastService
logger = logging.getLogger(__name__)


# ─── Device Monitor Job (added by Solar Forecast feature) ────
# Runs daily to check all production devices for missing data.
# Sends device_warning or feature_disabled notifications as needed.

async def run_device_monitor():
    """8:00 AM Saudi → check all production devices for missing data."""
    logger.info("Scheduler: Starting daily device monitor job...")
    try:
        monitor = DeviceMonitor(supabase_admin)
        monitor.run()
        logger.info("Scheduler: Device monitor job complete.")
    except Exception as e:
        logger.error(f"Scheduler: Device monitor job failed — {e}")


# ─── Solar Forecast Check Job (added by Solar Forecast feature) ──
# Runs daily to evaluate forecast state for all users.
# Sends forecast_ready notification if previous season data is complete.
# This ensures users receive the notification even without opening the app.

async def run_solar_forecast_check():
    """8:05 AM Saudi → check forecast state for all users.
    Sends forecast_ready notification if previous season is complete."""
    logger.info("Scheduler: Starting solar forecast check job...")
    try:
        from app.services.solar_forecast_service import SolarForecastService
        solar_svc = SolarForecastService(supabase_admin)
        response  = supabase_admin.table("users").select("user_id").execute()

        for user in (response.data or []):
            user_id = user.get("user_id")
            if not user_id:
                continue
            try:
                solar_svc.get_forecast_state(user_id)
            except Exception as e:
                logger.error(f"Scheduler: Forecast check failed for {user_id}: {e}")

        logger.info("Scheduler: Solar forecast check complete.")
    except Exception as e:
        logger.error(f"Scheduler: Solar forecast check job failed — {e}")


# ─── Helpers ─────────────────────────────────────────────────

async def _send_to_users(user_filter: str, recommendation_type: str):
    """
    Send recommendations to a filtered set of users.

    user_filter:
      - "solar"     → only users with has_solar_panels = True
      - "grid_only" → only users without solar
      - "all"       → all users (not used currently)

    recommendation_type:
      - "solar"   → custom solar recommendation
      - "general" → general tip
    """
    logger.info(
        f"Scheduler: Starting job — filter='{user_filter}', type='{recommendation_type}'"
    )

    try:
        response = supabase_admin.table("users").select(
            "user_id, has_solar_panels, energy_source"
        ).execute()
        users = response.data or []

        if not users:
            logger.info("Scheduler: No users found.")
            return

        facade = LuminFacade(supabase_admin)
        success_count = 0
        skip_count    = 0
        error_count   = 0

        for user in users:
            user_id = user.get("user_id")
            if not user_id:
                continue

            user_has_solar = Recommendation.userHasSolar(user)

            if user_filter == "solar" and not user_has_solar:
                continue
            if user_filter == "grid_only" and user_has_solar:
                continue

            try:
                result = facade.viewRecommendations(
                    user_id, recommendation_type=recommendation_type
                )

                if result.get("code") == "DAILY_LIMIT_REACHED":
                    skip_count += 1
                elif result.get("success"):
                    success_count += 1
                else:
                    skip_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Scheduler: Error for user {user_id}: {e}")

        logger.info(
            f"Scheduler [{user_filter}/{recommendation_type}]: "
            f"sent={success_count}, skipped={skip_count}, errors={error_count}"
        )

    except Exception as e:
        logger.error(f"Scheduler: Job failed — {e}")


# ─── Jobs ────────────────────────────────────────────────────

async def solar_users_custom_recommendation():
    """Saturday 3:00 PM Saudi → custom solar recommendation."""
    await _send_to_users(user_filter="solar", recommendation_type="solar")


async def solar_users_general_recommendation():
    """Tuesday 7:00 PM Saudi → general tip for solar users."""
    await _send_to_users(user_filter="solar", recommendation_type="general")


async def grid_users_general_recommendation_1():
    """Monday 4:00 PM Saudi → general tip for grid-only users."""
    await _send_to_users(user_filter="grid_only", recommendation_type="general")


async def grid_users_general_recommendation_2():
    """Thursday 8:00 PM Saudi → general tip for grid-only users."""
    await _send_to_users(user_filter="grid_only", recommendation_type="general")


# ─── Scheduler Instance ──────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    """
    Saudi time = UTC+3, so:
      3 PM Saudi = 12:00 UTC
      4 PM Saudi = 13:00 UTC
      7 PM Saudi = 16:00 UTC
      8 PM Saudi = 17:00 UTC
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # 8:00 AM Saudi = 05:00 UTC → Device Monitor (Solar Forecast feature)
    scheduler.add_job(
        run_device_monitor,
        trigger=CronTrigger(hour=5, minute=0),
        id="device_monitor_8am",
        name="Device Monitor at 8:00 AM Saudi",
        replace_existing=True,
    )

    # 8:05 AM Saudi = 05:05 UTC → Solar Forecast Check (Solar Forecast feature)
    scheduler.add_job(
        run_solar_forecast_check,
        trigger=CronTrigger(hour=5, minute=5),
        id="solar_forecast_check_8am",
        name="Solar Forecast Check at 8:05 AM Saudi",
        replace_existing=True,
    )

    # Saturday 3 PM Saudi → custom solar recommendation
    scheduler.add_job(
        solar_users_custom_recommendation,
        trigger=CronTrigger(day_of_week="sat", hour=12, minute=0),
        id="solar_custom_saturday_3pm",
        name="Solar users — custom recommendation (Saturday 3 PM Saudi)",
        replace_existing=True,
    )

    # Tuesday 7 PM Saudi → general tip for solar users
    scheduler.add_job(
        solar_users_general_recommendation,
        trigger=CronTrigger(day_of_week="tue", hour=16, minute=0),
        id="solar_general_tuesday_7pm",
        name="Solar users — general tip (Tuesday 7 PM Saudi)",
        replace_existing=True,
    )

    # Monday 4 PM Saudi → general tip for grid-only users
    scheduler.add_job(
        grid_users_general_recommendation_1,
        trigger=CronTrigger(day_of_week="mon", hour=13, minute=0),
        id="grid_general_monday_4pm",
        name="Grid-only users — general tip (Monday 4 PM Saudi)",
        replace_existing=True,
    )

    # Thursday 8 PM Saudi → general tip for grid-only users
    scheduler.add_job(
        grid_users_general_recommendation_2,
        trigger=CronTrigger(day_of_week="thu", hour=17, minute=0),
        id="grid_general_thursday_8pm",
        name="Grid-only users — general tip (Thursday 8 PM Saudi)",
        replace_existing=True,
    )

    return scheduler