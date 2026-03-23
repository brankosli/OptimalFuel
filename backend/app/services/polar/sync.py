"""
Polar sync service.
Pulls new exercises and sleep from Polar Accesslink and stores them
as normalised Activity and SleepRecord rows.
"""
import logging
import re
from datetime import datetime, date

from app.services.polar.client import polar_client
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, SleepRecord
from sqlalchemy import select

logger = logging.getLogger(__name__)


def _parse_duration(iso_duration: str) -> int:
    """Parse ISO 8601 duration PT1H23M45S → total seconds."""
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?"
    m = re.match(pattern, iso_duration or "PT0S")
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = float(m.group(3) or 0)
    return int(hours * 3600 + minutes * 60 + seconds)


def _map_sport(polar_sport: str) -> str:
    mapping = {
        "RUNNING": "run", "CYCLING": "ride", "SWIMMING": "swim",
        "STRENGTH_TRAINING": "strength", "HIKING": "hike",
        "ROWING": "rowing", "YOGA": "yoga", "CROSS_TRAINING": "crosstraining",
    }
    return mapping.get((polar_sport or "").upper(), (polar_sport or "other").lower())


async def sync_polar():
    if not polar_client.is_configured():
        logger.warning("Polar not configured — skipping. Run scripts/polar_auth.sh first.")
        return
    await _sync_exercises()
    await _sync_sleep()


async def _sync_exercises():
    try:
        exercises = await polar_client.list_exercises()
    except Exception as e:
        logger.error(f"Polar exercise fetch failed: {e}")
        return

    if not exercises:
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        for ex in exercises:
            source_id = f"polar_{ex.get('id')}"
            exists = await session.scalar(select(Activity).where(Activity.source_id == source_id))
            if exists:
                continue

            start_str = ex.get("start-time", "")
            try:
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                start_time = datetime.utcnow()

            activity = Activity(
                source="polar",
                source_id=source_id,
                activity_date=start_time.date(),
                start_time=start_time,
                duration_seconds=_parse_duration(ex.get("duration", "PT0S")),
                sport_type=_map_sport(ex.get("sport", "other")),
                name=ex.get("detailed-sport-info", {}).get("value"),
                calories=ex.get("calories"),
                distance_meters=ex.get("distance"),
                avg_heart_rate=(ex.get("heart-rate") or {}).get("average"),
                max_heart_rate=(ex.get("heart-rate") or {}).get("maximum"),
                training_load=(ex.get("training-load") or {}).get("score"),
                raw_data=ex,
            )
            session.add(activity)
            new_count += 1

        await session.commit()
        if new_count:
            logger.info(f"Polar: stored {new_count} new activities")


async def _sync_sleep():
    try:
        nights = await polar_client.get_sleep()
    except Exception as e:
        logger.error(f"Polar sleep fetch failed: {e}")
        return

    if not nights:
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        for night in nights:
            source_id = f"polar_sleep_{night.get('date')}"
            exists = await session.scalar(select(SleepRecord).where(SleepRecord.source_id == source_id))
            if exists:
                continue

            try:
                sleep_date = date.fromisoformat(night.get("date", ""))
            except (ValueError, AttributeError):
                continue

            recharge = night.get("nightly-recharge") or {}
            record = SleepRecord(
                source="polar",
                source_id=source_id,
                sleep_date=sleep_date,
                total_sleep_seconds=night.get("total-sleep-time-seconds"),
                light_sleep_seconds=(night.get("light-sleep") or {}).get("seconds"),
                deep_sleep_seconds=(night.get("deep-sleep") or {}).get("seconds"),
                rem_sleep_seconds=(night.get("rem-sleep") or {}).get("seconds"),
                sleep_score=night.get("sleep-score"),
                nightly_recharge_score=recharge.get("score"),
                ans_charge=recharge.get("ans-charge"),
                sleep_charge=recharge.get("sleep-charge"),
                hrv_avg_ms=night.get("heart-rate-variability-ms"),
                resting_hr=night.get("heart-rate-average"),
                breathing_rate=night.get("breathing-rate-average"),
                raw_data=night,
            )
            session.add(record)
            new_count += 1

        await session.commit()
        if new_count:
            logger.info(f"Polar: stored {new_count} new sleep records")
