from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def sync_all():
    """Main sync job — runs on schedule to pull latest data from Polar and Strava."""
    logger.info("🔄 Starting scheduled sync...")

    try:
        from app.services.polar.sync import sync_polar
        await sync_polar()
        logger.info("✅ Polar sync complete")
    except Exception as e:
        logger.error(f"❌ Polar sync failed: {e}")

    try:
        from app.services.strava.sync import sync_strava
        await sync_strava()
        logger.info("✅ Strava sync complete")
    except Exception as e:
        logger.error(f"❌ Strava sync failed: {e}")

    try:
        from app.services.analytics.pmc import recompute_daily_summaries
        await recompute_daily_summaries()
        logger.info("✅ Analytics recomputed")
    except Exception as e:
        logger.error(f"❌ Analytics recompute failed: {e}")


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_all,
        trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
        id="sync_all",
        name="Sync Polar + Strava + recompute analytics",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
