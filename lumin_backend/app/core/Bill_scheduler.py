from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.lumin_facade import LuminFacade
from datetime import datetime


scheduler = AsyncIOScheduler(timezone="Asia/Riyadh")


def setup_scheduler(facade: LuminFacade) -> None:
    """
    Register one daily bill checkpoint job.

    We run daily because every user has a different billing cycle.
    The facade decides whether each user reached checkpoint 7, 14, 21, or 28.
    """

    print("✅ Bill Scheduler setup called")

    if scheduler.running:
        return

   
    def bill_job_wrapper():
        print(f"BILL JOB TRIGGERED AT {datetime.now()}")
        facade.run_bill_checkpoint_for_all_users()

    
    scheduler.add_job(
        bill_job_wrapper,
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

    print("🛑 Bill Scheduler Stopped")

    if scheduler.running:
        scheduler.shutdown(wait=False)