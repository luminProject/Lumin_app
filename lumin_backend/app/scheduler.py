"""
scheduler.py

Runs automatic recommendation jobs for all users at:
  - 3:00 PM Saudi time (12:00 UTC)
  - 7:00 PM Saudi time (16:00 UTC)

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


# ─── Core Job ────────────────────────────────────────────────

async def send_recommendations_to_all_users():
    """
    Fetches all user IDs from the users table and generates
    a recommendation + notification for each one.
    Runs twice daily at 3 PM and 7 PM Saudi time.
    """
    logger.info("⚡ Scheduler: Starting recommendation job...")

    try:
        # Get all user IDs
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
                result = facade.viewRecommendations(user_id)

                if result.get("code") == "DAILY_LIMIT_REACHED":
                    skip_count += 1
                    logger.debug(f"Scheduler: Skipped {user_id} — daily limit reached.")
                elif result.get("success"):
                    success_count += 1
                    logger.debug(f"Scheduler: Sent recommendation to {user_id}.")
                else:
                    skip_count += 1
                    logger.debug(f"Scheduler: No recommendation for {user_id} — {result.get('code')}")

            except Exception as e:
                error_count += 1
                logger.error(f"Scheduler: Error for user {user_id}: {e}")

        logger.info(
            f"⚡ Scheduler: Done — "
            f"sent={success_count}, skipped={skip_count}, errors={error_count}"
        )

    except Exception as e:
        logger.error(f"⚡ Scheduler: Job failed — {e}")


# ─── Scheduler Instance ──────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    """
    Creates and configures the APScheduler instance.

    Schedule (Saudi time UTC+3):
      - 3:00 PM → 12:00 UTC
      - 7:00 PM → 16:00 UTC

    To change times, update hour/minute in the CronTrigger calls below.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # 3:00 PM Saudi = 12:00 UTC
    scheduler.add_job(
        send_recommendations_to_all_users,
        trigger=CronTrigger(hour=12, minute=0),
        id="recommendations_3pm",
        name="Recommendations at 3:00 PM Saudi",
        replace_existing=True,
    )

    # 7:00 PM Saudi = 16:00 UTC
    scheduler.add_job(
        send_recommendations_to_all_users,
        trigger=CronTrigger(hour=16, minute=0),
        id="recommendations_7pm",
        name="Recommendations at 7:00 PM Saudi",
        replace_existing=True,
    )

    return scheduler