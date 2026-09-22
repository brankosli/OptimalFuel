"""
Comparison endpoints — segment efforts and route grouping.
"""
import math
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import Activity, SegmentEffort
from app.services.strava.sync import sync_segments_for_rides

router = APIRouter()


def _fmt_time(seconds: int) -> str:
    """Format seconds as mm:ss or h:mm:ss."""
    if seconds is None:
        return "-"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ─── Segments ─────────────────────────────────────────────────────────────────

@router.get("/segments")
async def list_segments(db: AsyncSession = Depends(get_db)):
    """List all Strava segments with attempt stats."""
    rows = list(await db.execute(
        select(
            SegmentEffort.strava_segment_id,
            SegmentEffort.name,
            func.count(SegmentEffort.id).label("attempt_count"),
            func.min(SegmentEffort.elapsed_time).label("best_time"),
            func.max(SegmentEffort.effort_date).label("last_effort"),
            func.avg(SegmentEffort.avg_watts).label("avg_watts"),
            func.avg(SegmentEffort.avg_heart_rate).label("avg_hr"),
        )
        .group_by(SegmentEffort.strava_segment_id, SegmentEffort.name)
        .order_by(func.count(SegmentEffort.id).desc())
    ))

    return [
        {
            "segment_id": r.strava_segment_id,
            "name": r.name,
            "attempt_count": r.attempt_count,
            "best_time_seconds": r.best_time,
            "best_time_fmt": _fmt_time(r.best_time),
            "last_effort": r.last_effort.isoformat() if r.last_effort else None,
            "avg_watts": round(r.avg_watts, 1) if r.avg_watts else None,
            "avg_hr": round(r.avg_hr, 1) if r.avg_hr else None,
        }
        for r in rows
    ]


@router.get("/segments/{segment_id}")
async def get_segment_efforts(
    segment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """All efforts on a specific segment, sorted by date."""
    rows = list(await db.scalars(
        select(SegmentEffort)
        .where(SegmentEffort.strava_segment_id == segment_id)
        .order_by(SegmentEffort.effort_date.asc())
    ))

    if not rows:
        return {"segment_id": segment_id, "name": None, "efforts": []}

    best_time = min(r.elapsed_time for r in rows)

    return {
        "segment_id": segment_id,
        "name": rows[0].name,
        "best_time_seconds": best_time,
        "best_time_fmt": _fmt_time(best_time),
        "effort_count": len(rows),
        "efforts": [
            {
                "effort_id": r.strava_effort_id,
                "date": r.effort_date.isoformat(),
                "elapsed_time": r.elapsed_time,
                "elapsed_time_fmt": _fmt_time(r.elapsed_time),
                "moving_time": r.moving_time,
                "avg_heart_rate": r.avg_heart_rate,
                "avg_watts": r.avg_watts,
                "avg_cadence": r.avg_cadence,
                "pr_rank": r.pr_rank,
                "is_pr": r.pr_rank == 1,
                "delta_from_best": r.elapsed_time - best_time,
            }
            for r in rows
        ],
    }


# ─── Routes (heuristic grouping) ──────────────────────────────────────────────

def _route_key(start_lat: float, start_lng: float, distance_meters: float) -> Optional[str]:
    """
    Group rides by start point (±~1km) and distance (±2km bucket).
    Returns a stable string key or None if data is missing.
    """
    if start_lat is None or start_lng is None or not distance_meters:
        return None
    lat = round(start_lat, 2)
    lng = round(start_lng, 2)
    dist_bucket = round(distance_meters / 2000) * 2  # nearest 2km
    return f"{lat}_{lng}_{dist_bucket}"


@router.get("/routes")
async def list_routes(db: AsyncSession = Depends(get_db)):
    """
    Group cycling activities by heuristic route matching.
    Returns route groups with attempt count and performance stats.
    """
    rows = list(await db.scalars(
        select(Activity)
        .where(
            Activity.source == "strava",
            Activity.sport_type == "ride",
            Activity.start_lat != None,
        )
        .order_by(Activity.activity_date.desc())
    ))

    groups: dict[str, list] = {}
    for act in rows:
        key = _route_key(act.start_lat, act.start_lng, act.distance_meters)
        if not key:
            continue
        groups.setdefault(key, []).append(act)

    result = []
    for key, acts in groups.items():
        if len(acts) < 2:
            continue  # only show routes with at least 2 attempts
        most_recent = acts[0]
        best_duration = min(a.duration_seconds for a in acts)
        avg_power = None
        power_acts = [a.avg_power_watts for a in acts if a.avg_power_watts]
        if power_acts:
            avg_power = round(sum(power_acts) / len(power_acts), 1)

        result.append({
            "route_key": key,
            "name": most_recent.name,
            "attempt_count": len(acts),
            "distance_km": round((most_recent.distance_meters or 0) / 1000, 1),
            "elevation_gain_m": round(most_recent.elevation_gain_meters or 0),
            "best_duration_seconds": best_duration,
            "best_duration_fmt": _fmt_time(best_duration),
            "last_ride": acts[0].activity_date.isoformat(),
            "avg_power": avg_power,
            "summary_polyline": most_recent.summary_polyline,
        })

    result.sort(key=lambda x: x["attempt_count"], reverse=True)
    return result


@router.get("/routes/{route_key:path}")
async def get_route_rides(
    route_key: str,
    db: AsyncSession = Depends(get_db),
):
    """All rides in a route group, sorted by date."""
    rows = list(await db.scalars(
        select(Activity)
        .where(
            Activity.source == "strava",
            Activity.sport_type == "ride",
            Activity.start_lat != None,
        )
        .order_by(Activity.activity_date.asc())
    ))

    # Filter to matching route key
    matching = [a for a in rows if _route_key(a.start_lat, a.start_lng, a.distance_meters) == route_key]

    if not matching:
        return {"route_key": route_key, "name": None, "rides": []}

    best_duration = min(a.duration_seconds for a in matching)

    return {
        "route_key": route_key,
        "name": matching[-1].name,  # most recent name
        "distance_km": round((matching[0].distance_meters or 0) / 1000, 1),
        "ride_count": len(matching),
        "best_duration_seconds": best_duration,
        "best_duration_fmt": _fmt_time(best_duration),
        "rides": [
            {
                "id": a.id,
                "date": a.activity_date.isoformat(),
                "name": a.name,
                "duration_seconds": a.duration_seconds,
                "duration_fmt": _fmt_time(a.duration_seconds),
                "distance_km": round((a.distance_meters or 0) / 1000, 1),
                "elevation_gain_m": round(a.elevation_gain_meters or 0),
                "avg_heart_rate": a.avg_heart_rate,
                "avg_power_watts": a.avg_power_watts,
                "normalized_power_watts": a.normalized_power_watts,
                "tss": a.tss,
                "delta_from_best": a.duration_seconds - best_duration,
                "summary_polyline": a.summary_polyline,
            }
            for a in matching
        ],
    }


# ─── Backfill trigger ─────────────────────────────────────────────────────────

@router.post("/sync")
async def trigger_segment_sync(background_tasks: BackgroundTasks):
    """Manually trigger segment + GPS backfill for unsynced rides."""
    background_tasks.add_task(sync_segments_for_rides)
    return {"message": "Segment sync started in background"}
