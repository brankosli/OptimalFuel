"""
Activity deduplication service.

Problem: Polar V3 auto-syncs to both Polar Flow AND Strava.
Every session appears twice — polar_XXXXX and strava_XXXXX.
This inflates TSS, CTL/ATL and ruins all analytics.

Strategy:
- Strava is PRIMARY (richer data — GPS, segments, suffer score)
- Polar exercise is SECONDARY — marked polar_dedup if Strava match found
- Match = same day + start times within 30 minutes
- Soft-delete only (source set to "polar_dedup") — data preserved
"""
from datetime import timedelta
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Activity

MATCH_WINDOW = timedelta(minutes=30)


async def dedup_activities():
    async with AsyncSessionLocal() as session:
        all_acts = list(await session.scalars(
            select(Activity).order_by(Activity.activity_date, Activity.start_time)
        ))

        strava_acts = [a for a in all_acts if a.source == "strava"]
        polar_acts  = [a for a in all_acts if a.source == "polar"]

        if not strava_acts or not polar_acts:
            print("Dedup: nothing to deduplicate")
            return

        # Index Strava by date for fast lookup
        strava_by_date: dict = {}
        for a in strava_acts:
            strava_by_date.setdefault(a.activity_date.isoformat(), []).append(a)

        found = 0
        for polar_act in polar_acts:
            key = polar_act.activity_date.isoformat()
            for strava_act in strava_by_date.get(key, []):
                diff = abs(
                    polar_act.start_time.replace(tzinfo=None) -
                    strava_act.start_time.replace(tzinfo=None)
                )
                if diff <= MATCH_WINDOW:
                    polar_act.source = "polar_dedup"
                    found += 1
                    break

        if found:
            await session.commit()
            print(f"Dedup: marked {found} Polar activities as Strava duplicates")
        else:
            print("Dedup: no duplicates found")
