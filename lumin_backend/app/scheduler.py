"""
scheduler.py

Runs automatic recommendation jobs based on user type:

For Solar users (Grid + Solar):
  - Saturday 3:00 PM Saudi time → Solar (custom) recommendation
  - Tuesday 7:00 PM Saudi time → General recommendation

For Grid-only users:
  - Monday 4:00 PM Saudi time → General recommendation
  - Thursday 8:00 PM Saudi time → General recommendation

Also runs Solar Forecast jobs daily (Sprint 2 — Solar Forecast feature):
  - 8:00 AM Saudi time (05:00 UTC) → Device Monitor
  - 8:05 AM Saudi time (05:05 UTC) → Solar Forecast Check

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
from app.tasks.device_monitor import DeviceMonitor
from app.models.solar_forecast_service import SolarForecastService  # Sprint 2

logger = logging.getLogger(__name__)


# ─── Device Monitor Job ──────────────────────────────────────
# Sprint 2 — Solar Forecast feature.
# Runs daily to check all production devices for missing data.
# Sends device_warning or feature_disabled via DatabaseManager + FCMService.
# See Change Log v4, Section 3.12.

async def run_device_monitor():
    """8:00 AM Saudi → check all production devices for missing data."""
    logger.info("Scheduler: Starting daily device monitor job...")
    try:
        monitor = DeviceMonitor(supabase_admin)
        monitor.run()
        logger.info("Scheduler: Device monitor job complete.")
    except Exception as e:
        logger.error(f"Scheduler: Device monitor job failed — {e}")


# ─── Solar Forecast Check Job ────────────────────────────────
# Sprint 2 — Solar Forecast feature.
# Runs daily to evaluate forecast state for all users.
# Sends forecast_ready notification if previous season is complete (≥ 45 days).
# Cases: no_panels | collecting | collecting_extended |
#        forecast_available | feature_disabled
# See Change Log v4, Section 3.14.

async def run_solar_forecast_check():
    """8:05 AM Saudi → check forecast state for all users."""
    logger.info("Scheduler: Starting solar forecast check job...")
    try:
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


# ─── Daily Reset Job ─────────────────────────────────────────

async def reset_daily_energy():
    """
    12:00 AM Saudi (21:00 UTC previous day) → reset total_energy_daily
    for ALL devices to 0. Called once per day at midnight Saudi time.
    """
    logger.info("Scheduler: Resetting total_energy_daily for all devices...")
    try:
        facade = LuminFacade(supabase_admin)
        facade.resetDailyEnergy()
        logger.info("Scheduler: total_energy_daily reset complete.")
    except Exception as e:
        logger.error(f"Scheduler: Daily reset failed — {e}")


# ─── Energy Calculation Job ───────────────────────────────────

async def update_energy_calculation():
    """
    Every minute → sum total_energy_daily per user from device table,
    then UPSERT into energycalculation (one row per user per day).
    Used by bill prediction and statistics features.
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    from app.core.database_manager import DatabaseManager

    logger.info("Scheduler: Updating energycalculation...")
    try:
        db = DatabaseManager(supabase_admin)
        today = datetime.now(ZoneInfo("Asia/Riyadh")).date().isoformat()

        user_ids = db.get_all_user_ids()
        for user_id in user_ids:
            try:
                totals = db.get_user_daily_energy_totals(user_id)
                db.upsert_energy_calculation(
                    user_id=user_id,
                    date_str=today,
                    total_consumption=totals["total_consumption"],
                    solar_production=totals["solar_production"],
                )
            except Exception as e:
                logger.error(f"Scheduler: Energy calc failed for {user_id}: {e}")

        logger.info(f"Scheduler: energycalculation updated for {len(user_ids)} users.")
    except Exception as e:
        logger.error(f"Scheduler: Energy calculation job failed — {e}")


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

    # 8:00 AM Saudi = 05:00 UTC → Device Monitor (Sprint 2)
    scheduler.add_job(
        run_device_monitor,
        trigger=CronTrigger(hour=5, minute=0),
        id="device_monitor_8am",
        name="Device Monitor at 8:00 AM Saudi",
        replace_existing=True,
    )

    # 8:05 AM Saudi = 05:05 UTC → Solar Forecast Check (Sprint 2)
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

    # 12:00 AM Saudi = 21:00 UTC → Reset total_energy_daily
    scheduler.add_job(
        reset_daily_energy,
        trigger=CronTrigger(hour=21, minute=0),
        id="reset_daily_energy_midnight",
        name="Reset total_energy_daily at midnight Saudi",
        replace_existing=True,
    )

    # Every minute → UPSERT energycalculation
    scheduler.add_job(
        update_energy_calculation,
        trigger=CronTrigger(minute="*"),
        id="update_energy_calculation_every_minute",
        name="Update energycalculation every minute",
        replace_existing=True,
    )

    return scheduler