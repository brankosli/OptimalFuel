"""
Polar sync service.
Pulls exercises and sleep from Polar Accesslink and stores as
normalised Activity and SleepRecord rows.

Field names verified from live API response.
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
    """Parse ISO 8601 duration PT1H23M45S to total seconds."""
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


def _avg_hr_from_samples(samples: dict) -> int | None:
    """Compute average HR from Polar's heart_rate_samples dict."""
    if not samples:
        return None
    values = list(samples.values())
    if not values:
        return None
    return round(sum(values) / len(values))


async def sync_polar():
    if not polar_client.is_configured():
        print("Polar not configured — skipping")
        return
    await _sync_exercises()
    await _sync_sleep()


async def _sync_exercises():
    try:
        exercises = await polar_client.list_exercises()
    except Exception as e:
        print(f"Polar exercise fetch failed: {e}")
        return

    if not exercises:
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        for ex in exercises:
            source_id = f"polar_{ex.get('id')}"
            exists = await session.scalar(
                select(Activity).where(Activity.source_id == source_id)
            )
            if exists:
                continue

            # Polar new exercise endpoint uses snake_case
            start_str = ex.get("start_time", "")
            try:
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                start_time = datetime.utcnow()

            hr = ex.get("heart_rate") or {}
            activity = Activity(
                source="polar",
                source_id=source_id,
                activity_date=start_time.date(),
                start_time=start_time,
                duration_seconds=_parse_duration(ex.get("duration", "PT0S")),
                sport_type=_map_sport(ex.get("sport", "other")),
                name=ex.get("detailed_sport_info"),
                calories=ex.get("calories"),
                distance_meters=ex.get("distance"),
                avg_heart_rate=hr.get("average"),
                max_heart_rate=hr.get("maximum"),
                training_load=ex.get("training_load"),
                raw_data={k: ex[k] for k in ("id", "sport", "calories") if k in ex},
            )
            session.add(activity)
            new_count += 1

        await session.commit()
        if new_count:
            print(f"Polar: stored {new_count} new exercises")


async def _sync_sleep():
    try:
        nights = await polar_client.get_sleep()
    except Exception as e:
        print(f"Polar sleep fetch failed: {e}")
        return

    if not nights:
        print("Polar: no sleep records to store")
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        updated_count = 0

        for night in nights:
            # Polar returns date as "YYYY-MM-DD"
            date_str = night.get("date", "")
            try:
                sleep_date = date.fromisoformat(date_str)
            except (ValueError, AttributeError):
                continue

            source_id = f"polar_sleep_{date_str}"

            # Polar field names from live API:
            # light_sleep, deep_sleep, rem_sleep  → already in SECONDS
            # sleep_score                         → 0-100
            # sleep_charge                        → 0-5 scale
            # sleep_start_time, sleep_end_time    → ISO datetime strings
            # heart_rate_samples                  → dict of time:bpm
            # unrecognized_sleep_stage            → seconds

            light = night.get("light_sleep")       # seconds
            deep  = night.get("deep_sleep")        # seconds
            rem   = night.get("rem_sleep")         # seconds
            unrecognized = night.get("unrecognized_sleep_stage", 0) or 0

            # Total sleep = all stages combined
            total = None
            if any(v is not None for v in [light, deep, rem]):
                total = (light or 0) + (deep or 0) + (rem or 0) + unrecognized

            # Parse bedtime / wake time
            bedtime = None
            wake_time = None
            try:
                if night.get("sleep_start_time"):
                    bedtime = datetime.fromisoformat(night["sleep_start_time"])
                if night.get("sleep_end_time"):
                    wake_time = datetime.fromisoformat(night["sleep_end_time"])
            except (ValueError, AttributeError):
                pass

            # Average HR from samples
            resting_hr = _avg_hr_from_samples(night.get("heart_rate_samples"))

            existing = await session.scalar(
                select(SleepRecord).where(SleepRecord.source_id == source_id)
            )

            if existing:
                # Update with real values (previous sync may have stored nulls)
                existing.total_sleep_seconds = total
                existing.light_sleep_seconds = light
                existing.deep_sleep_seconds  = deep
                existing.rem_sleep_seconds   = rem
                existing.sleep_score         = night.get("sleep_score")
                existing.sleep_charge        = night.get("sleep_charge")
                existing.resting_hr          = resting_hr
                existing.bedtime             = bedtime
                existing.wake_time           = wake_time
                existing.raw_data            = {k: night[k] for k in
                    ("date", "sleep_score", "light_sleep", "deep_sleep", "rem_sleep",
                     "sleep_charge", "continuity", "sleep_cycles") if k in night}
                updated_count += 1
            else:
                record = SleepRecord(
                    source="polar",
                    source_id=source_id,
                    sleep_date=sleep_date,
                    bedtime=bedtime,
                    wake_time=wake_time,
                    total_sleep_seconds=total,
                    light_sleep_seconds=light,
                    deep_sleep_seconds=deep,
                    rem_sleep_seconds=rem,
                    sleep_score=night.get("sleep_score"),
                    sleep_charge=night.get("sleep_charge"),
                    resting_hr=resting_hr,
                    raw_data={k: night[k] for k in
                        ("date", "sleep_score", "light_sleep", "deep_sleep", "rem_sleep",
                         "sleep_charge", "continuity", "sleep_cycles") if k in night},
                )
                session.add(record)
                new_count += 1

        await session.commit()
        print(f"Polar: {new_count} new + {updated_count} updated sleep records")