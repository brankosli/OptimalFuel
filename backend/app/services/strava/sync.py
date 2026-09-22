"""
Strava sync service.
Pulls new activities, computes TSS, and backfills TSS
for existing activities that have null TSS.
"""
import logging
from datetime import datetime, timezone

from app.services.strava.client import strava_client
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, SegmentEffort, UserProfile
from sqlalchemy import select

logger = logging.getLogger(__name__)

SPORT_MAP = {
    "Run": "run", "TrailRun": "run", "VirtualRun": "run",
    "Ride": "ride", "VirtualRide": "ride", "EBikeRide": "ride",
    "Swim": "swim", "Workout": "workout", "WeightTraining": "strength",
    "Yoga": "yoga", "Hike": "hike", "Walk": "walk",
    "Rowing": "rowing", "Kayaking": "kayaking", "Snowboard": "ski",
    "NordicSki": "ski", "Soccer": "soccer",
}


def _map_sport(strava_type: str) -> str:
    return SPORT_MAP.get(strava_type, (strava_type or "other").lower())


# ─── TSS Calculation ──────────────────────────────────────────────────────────

def compute_tss_from_power(duration_seconds: int, normalized_power: float, ftp: float) -> float:
    if not ftp or not normalized_power or duration_seconds <= 0:
        return 0.0
    intensity_factor = normalized_power / ftp
    return (duration_seconds * normalized_power * intensity_factor) / (ftp * 3600) * 100


def compute_tss_from_hr(duration_seconds: int, avg_hr: int, lthr: int, hr_rest: int = 50) -> float:
    if not lthr or not avg_hr or duration_seconds <= 0:
        return 0.0
    hr_reserve_ratio = (avg_hr - hr_rest) / (lthr - hr_rest)
    hr_reserve_ratio = max(0.0, min(hr_reserve_ratio, 1.5))
    trimp = (duration_seconds / 60) * hr_reserve_ratio * 0.64 * (2.718 ** (1.92 * hr_reserve_ratio))
    trimp_at_lthr_1hr = 60 * 1.0 * 0.64 * (2.718 ** 1.92)
    return trimp * (100 / trimp_at_lthr_1hr)


def _calc_tss(duration, avg_hr, np_watts, avg_watts, ftp, lthr):
    if np_watts and ftp:
        return compute_tss_from_power(duration, np_watts, ftp)
    if avg_watts and ftp:
        return compute_tss_from_power(duration, avg_watts, ftp)
    if avg_hr and lthr:
        return compute_tss_from_hr(duration, int(avg_hr), lthr)
    return None


# ─── Main sync ────────────────────────────────────────────────────────────────

async def sync_strava():
    if not strava_client.is_configured():
        print("Strava not configured — skipping")
        return

    # Load profile
    async with AsyncSessionLocal() as session:
        last = await session.scalar(
            select(Activity)
            .where(Activity.source == "strava")
            .order_by(Activity.start_time.desc())
            .limit(1)
        )
        after_ts = int(last.start_time.timestamp()) + 1 if last else 0
        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))
        ftp  = profile.ftp_watts if profile else None
        lthr = profile.lthr_bpm if profile else None

    print(f"Strava: syncing since ts={after_ts}, FTP={ftp}, LTHR={lthr}")

    # Fetch new activities
    try:
        activities = await strava_client.list_all_activities_since(after_ts)
    except Exception as e:
        print(f"Strava activity fetch failed: {e}")
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        for act in activities:
            source_id = f"strava_{act['id']}"
            if await session.scalar(select(Activity).where(Activity.source_id == source_id)):
                continue

            start_str = act.get("start_date", "")
            try:
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                start_time = datetime.utcnow()

            duration  = act.get("moving_time", 0) or act.get("elapsed_time", 0)
            avg_hr    = act.get("average_heartrate")
            np_watts  = act.get("weighted_average_watts")
            avg_watts = act.get("average_watts")
            tss       = _calc_tss(duration, avg_hr, np_watts, avg_watts, ftp, lthr)

            session.add(Activity(
                source="strava",
                source_id=source_id,
                activity_date=start_time.date(),
                start_time=start_time,
                duration_seconds=duration,
                sport_type=_map_sport(act.get("sport_type") or act.get("type", "other")),
                name=act.get("name"),
                calories=act.get("calories"),
                distance_meters=act.get("distance"),
                elevation_gain_meters=act.get("total_elevation_gain"),
                avg_heart_rate=int(avg_hr) if avg_hr else None,
                max_heart_rate=act.get("max_heartrate"),
                suffer_score=act.get("suffer_score"),
                tss=round(tss, 1) if tss else None,
                avg_power_watts=avg_watts,
                normalized_power_watts=np_watts,
                ftp_watts=ftp,
                raw_data={k: act[k] for k in ("id", "name", "type", "sport_type", "suffer_score") if k in act},
            ))
            new_count += 1

        await session.commit()
        if new_count:
            print(f"Strava: stored {new_count} new activities")

    # Sync GPS + segments for rides not yet processed
    await sync_segments_for_rides()

    # Always backfill TSS for existing activities with null TSS
    # This handles the case where LTHR/FTP was set AFTER activities were synced
    await _backfill_tss(ftp, lthr)


# ─── Segment + GPS Sync ───────────────────────────────────────────────────────

async def _sync_activity_details(activity: Activity, session):
    """Fetch full activity detail from Strava and store GPS + segment efforts."""
    strava_id = int(activity.source_id.replace("strava_", ""))
    try:
        detail = await strava_client.get_activity(strava_id)
    except Exception as e:
        logger.warning(f"Could not fetch detail for activity {strava_id}: {e}")
        activity.segments_synced = True  # mark done so we don't retry forever
        return

    # GPS data
    start_latlng = detail.get("start_latlng") or []
    end_latlng   = detail.get("end_latlng") or []
    activity.start_lat = start_latlng[0] if len(start_latlng) == 2 else None
    activity.start_lng = start_latlng[1] if len(start_latlng) == 2 else None
    activity.end_lat   = end_latlng[0]   if len(end_latlng) == 2   else None
    activity.end_lng   = end_latlng[1]   if len(end_latlng) == 2   else None
    activity.summary_polyline = (detail.get("map") or {}).get("summary_polyline")

    # Segment efforts
    efforts = detail.get("segment_efforts") or []
    for e in efforts:
        seg = e.get("segment") or {}
        effort_id = e.get("id")
        if not effort_id:
            continue
        # Skip if already stored
        existing = await session.scalar(
            select(SegmentEffort).where(SegmentEffort.strava_effort_id == effort_id)
        )
        if existing:
            continue

        start_str = e.get("start_date") or e.get("start_date_local", "")
        try:
            effort_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            effort_date = effort_dt.date()
        except (ValueError, AttributeError):
            effort_date = activity.activity_date

        session.add(SegmentEffort(
            activity_id=activity.id,
            strava_segment_id=seg.get("id", 0),
            strava_effort_id=effort_id,
            name=seg.get("name", e.get("name", "Unknown")),
            effort_date=effort_date,
            elapsed_time=e.get("elapsed_time", 0),
            moving_time=e.get("moving_time"),
            distance_meters=e.get("distance"),
            avg_heart_rate=e.get("average_heartrate"),
            avg_watts=e.get("average_watts"),
            avg_cadence=e.get("average_cadence"),
            pr_rank=e.get("pr_rank"),
            kom_rank=e.get("kom_rank"),
        ))

    activity.segments_synced = True


async def sync_segments_for_rides():
    """
    Backfill GPS and segment efforts for all Ride activities not yet synced.
    Processes up to 30 per run to stay within Strava rate limits.
    """
    if not strava_client.is_configured():
        return

    async with AsyncSessionLocal() as session:
        rides = list(await session.scalars(
            select(Activity)
            .where(
                Activity.source == "strava",
                Activity.sport_type == "ride",
                Activity.segments_synced == False,
            )
            .order_by(Activity.activity_date.desc())
            .limit(30)
        ))

        if not rides:
            print("Segments: all rides already synced ✓")
            return

        print(f"Segments: fetching details for {len(rides)} rides...")
        for activity in rides:
            await _sync_activity_details(activity, session)

        await session.commit()
        print(f"Segments: synced {len(rides)} rides")


# ─── TSS Backfill ─────────────────────────────────────────────────────────────

async def _backfill_tss(ftp, lthr):
    """
    Recalculate TSS for all Strava activities where TSS is null.
    Runs on every sync — fast since it skips activities that already have TSS.

    This is critical because:
    - User sets LTHR after first sync → old activities have null TSS
    - DB was deleted and resynced before profile was saved → same problem
    """
    if not ftp and not lthr:
        print("Strava: skipping TSS backfill — no LTHR or FTP in profile")
        return

    async with AsyncSessionLocal() as session:
        rows = list(await session.scalars(
            select(Activity).where(
                Activity.source == "strava",
                Activity.tss == None,
            )
        ))

        if not rows:
            print("Strava: all activities already have TSS ✓")
            return

        updated = 0
        for act in rows:
            tss = _calc_tss(
                act.duration_seconds,
                act.avg_heart_rate,
                act.normalized_power_watts,
                act.avg_power_watts,
                ftp,
                lthr,
            )
            if tss:
                act.tss = round(tss, 1)
                act.ftp_watts = ftp
                updated += 1

        await session.commit()
        print(f"Strava: backfilled TSS for {updated}/{len(rows)} activities")