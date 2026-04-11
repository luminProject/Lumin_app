"""
scheduler.py

Runs automatic recommendation jobs for all users at:
  - 3:00 PM Saudi time (12:00 UTC) → Solar recommendation (or general if no solar)
  - 7:00 PM Saudi time (16:00 UTC) → General recommendation for all users

Uses APScheduler with FastAPI lifespan.
Install: pip install apscheduler
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.supabase_client import supabase_admin
from app.core.lumin_facade import LuminFacade

logger = logging.getLogger(__name__)


# ─── Helper ──────────────────────────────────────────────────

async def _send_to_all_users(recommendation_type: str):
    logger.info(f"Scheduler: Starting '{recommendation_type}' recommendation job...")

    try:
        response = supabase_admin.table("users").select("user_id").execute()
        users = response.data or []

        if not users:
            logger.info("Scheduler: No users found.")
            return

        facade = LuminFacade(supabase_admin)
        success_count = 0
        skip_count = 0
        error_count = 0

        for user in users:
            user_id = user.get("user_id")
            if not user_id:
                continue

            try:
                result = facade.viewRecommendations(user_id, recommendation_type=recommendation_type)

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
            f"Scheduler [{recommendation_type}]: Done — "
            f"sent={success_count}, skipped={skip_count}, errors={error_count}"
        )

    except Exception as e:
        logger.error(f"Scheduler: Job failed — {e}")


# ─── Jobs ────────────────────────────────────────────────────

async def send_solar_recommendations():
    """3:00 PM Saudi → Solar recommendation (weekly) or general fallback."""
    await _send_to_all_users("solar")


async def send_general_recommendations():
    """7:00 PM Saudi → General recommendation for all users."""
    await _send_to_all_users("general")


# ─── Scheduler Instance ──────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # 3:00 PM Saudi = 12:00 UTC → Solar
    scheduler.add_job(
        send_solar_recommendations,
        trigger=CronTrigger(hour=12, minute=0),
        id="recommendations_solar_3pm",
        name="Solar Recommendations at 3:00 PM Saudi",
        replace_existing=True,
    )

    # 7:00 PM Saudi = 16:00 UTC → General
    scheduler.add_job(
        send_general_recommendations,
        trigger=CronTrigger(hour=16, minute=0),
        id="recommendations_general_7pm",
        name="General Recommendations at 7:00 PM Saudi",
        replace_existing=True,
    )

    return scheduler