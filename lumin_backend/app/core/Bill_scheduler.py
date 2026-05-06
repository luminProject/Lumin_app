from apscheduler.schedulers.background import BackgroundScheduler
from app.core.lumin_facade import LuminFacade


scheduler = BackgroundScheduler(timezone="Asia/Riyadh")


def setup_scheduler(facade: LuminFacade) -> None:
    """
    Register one daily bill checkpoint job.

    We run daily because every user has a different billing cycle.
    The facade decides whether each user reached checkpoint 7, 14, 21, or 28.
    """
    print("✅ Bill Scheduler setup called")

    if scheduler.running:
        return

    scheduler.add_job(
        lambda: facade.run_bill_checkpoint_for_all_users(),
        trigger="cron",
        hour=12,
        minute=0,
        id="bill_daily_checkpoint_job",
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