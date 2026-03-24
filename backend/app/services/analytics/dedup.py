"""
Activity deduplication service.

Problem: Polar V3 syncs to both Polar Flow and Strava automatically.
This means every recorded session appears twice in the DB:
  - polar_XXXXX  (from Polar Accesslink)
  - strava_XXXXX (from Strava API)

Strategy:
  - Strava is the PRIMARY source — richer data (GPS, segments, suffer score)
  - Polar exercises are SECONDARY — only kept if no matching Strava activity exists
  - A match = same day + start times within 30 minutes of each other
  - Duplicates are soft-deleted by setting source to "polar_dedup" (not hard deleted,
    preserving the raw data in case we ever need it)

Run after both Polar and Strava syncs complete.
"""
from datetime import timedelta
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.models import Activity


MATCH_WINDOW_MINUTES = 30   # activities within this window on same day = duplicate


async def dedup_activities():
    """
    Find Polar activities that duplicate a Strava activity and mark them.
    Returns count of duplicates found.
    """
    async with AsyncSessionLocal() as session:
        # Load all activities ordered by date
        all_activities = list(await session.scalars(
            select(Activity).order_by(Activity.activity_date, Activity.start_time)
        ))

        # Separate by source — exclude already-deduped
        strava_acts = [a for a in all_activities if a.source == "strava"]
        polar_acts  = [a for a in all_activities if a.source == "polar"]

        if not strava_acts or not polar_acts:
            return 0

        # Build a lookup of Strava activities by date for fast matching
        strava_by_date: dict[str, list[Activity]] = {}
        for a in strava_acts:
            key = a.activity_date.isoformat()
            strava_by_date.setdefault(key, []).append(a)

        duplicates_found = 0
        window = timedelta(minutes=MATCH_WINDOW_MINUTES)

        for polar_act in polar_acts:
            key = polar_act.activity_date.isoformat()
            same_day_strava = strava_by_date.get(key, [])

            for strava_act in same_day_strava:
                # Check if start times are within the match window
                time_diff = abs(
                    polar_act.start_time.replace(tzinfo=None) -
                    strava_act.start_time.replace(tzinfo=None)
                )
                if time_diff <= window:
                    # Mark Polar activity as duplicate
                    polar_act.source = "polar_dedup"
                    duplicates_found += 1
                    break   # one match is enough

        if duplicates_found:
            await session.commit()
            print(f"Dedup: marked {duplicates_found} Polar activities as duplicates of Strava records")
        else:
            print("Dedup: no duplicates found")

        return duplicates_found


async def restore_dedup():
    """
    Restore all deduped Polar activities back to active.
    Useful if you want to re-run deduplication from scratch.
    """
    async with AsyncSessionLocal() as session:
        rows = list(await session.scalars(
            select(Activity).where(Activity.source == "polar_dedup")
        ))
        for a in rows:
            a.source = "polar"
        await session.commit()
        print(f"Dedup: restored {len(rows)} Polar activities")
