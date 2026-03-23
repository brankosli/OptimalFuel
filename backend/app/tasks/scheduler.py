from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
import logging
logger = logging.getLogger(__name__)


async def sync_all():
    print("🔄 sync_all started...")

    try:
        from app.services.polar.sync import sync_polar
        print("▶ Running Polar sync...")
        await sync_polar()
        print("✅ Polar sync done")
    except Exception as e:
        print(f"❌ Polar sync failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        from app.services.strava.sync import sync_strava
        print("▶ Running Strava sync...")
        await sync_strava()
        print("✅ Strava sync done")
    except Exception as e:
        print(f"❌ Strava sync failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        from app.services.analytics.pmc import recompute_daily_summaries
        print("▶ Recomputing analytics...")
        await recompute_daily_summaries()
        print("✅ Analytics done")
    except Exception as e:
        print(f"❌ Analytics failed: {e}")
        import traceback
        traceback.print_exc()

    print("🏁 sync_all finished")


def start_scheduler():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from app.core.config import settings
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_all,
        trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
        id="sync_all",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler