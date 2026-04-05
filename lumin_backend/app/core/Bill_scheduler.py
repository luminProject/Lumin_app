from apscheduler.schedulers.background import BackgroundScheduler
from app.core.lumin_facade import LuminFacade


scheduler = BackgroundScheduler(timezone="Asia/Riyadh")


def setup_scheduler(facade: LuminFacade) -> None:
    """
    Register all scheduled bill checkpoint jobs.
    Safe to call once at startup.
    """
    print("✅ Bill Scheduler setup called")
    if scheduler.running:
        return

    scheduler.add_job(
        
        lambda: facade.run_bill_checkpoint_for_all_users(7),
        trigger="cron",
        day=8,
        hour=12,
        minute=0,
        id="bill_checkpoint_day_7",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: facade.run_bill_checkpoint_for_all_users(14),
        trigger="cron",
        day=15,
        hour=12,
        minute=0,
        id="bill_checkpoint_day_14",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: facade.run_bill_checkpoint_for_all_users(21),
        trigger="cron",
        day=22,
        hour=12,
        minute=0,
        id="bill_checkpoint_day_21",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: facade.run_bill_checkpoint_for_all_users(28),
        trigger="cron",
        day=28,
        hour=23,
        minute=55,
        id="bill_checkpoint_day_28",
        replace_existing=True,
    )

    scheduler.start()
    print("✅ Bill Scheduler Started")


def shutdown_scheduler() -> None:
    """
    Stop scheduler safely on app shutdown.
    """
    print("✅ Bill Scheduler Stopped")
    if scheduler.running:
        scheduler.shutdown(wait=False)