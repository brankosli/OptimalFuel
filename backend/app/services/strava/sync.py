"""
Strava sync service.
Pulls new activities from Strava API, computes TSS where possible,
and stores as normalised Activity rows.
"""
import logging
from datetime import datetime, timezone

from app.services.strava.client import strava_client
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, UserProfile
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ─── Sport type normalisation ─────────────────────────────────────────────────

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

def compute_tss_from_power(
    duration_seconds: int,
    normalized_power: float,
    ftp: float,
) -> float:
    """
    Training Stress Score from power data.
    TSS = (duration_s * NP * IF) / (FTP * 3600) * 100
    where IF = NP / FTP (Intensity Factor)
    """
    if not ftp or not normalized_power or duration_seconds <= 0:
        return 0.0
    intensity_factor = normalized_power / ftp
    return (duration_seconds * normalized_power * intensity_factor) / (ftp * 3600) * 100


def compute_tss_from_hr(
    duration_seconds: int,
    avg_hr: int,
    lthr: int,
    hr_rest: int = 50,
) -> float:
    """
    HR-based TSS approximation (hrTSS).
    Uses TRIMP approach scaled to TSS range.
    Less accurate than power-based but works for all sports.

    Formula based on Banister's TRIMP with gender-neutral coefficient.
    """
    if not lthr or not avg_hr or duration_seconds <= 0:
        return 0.0

    hr_reserve_ratio = (avg_hr - hr_rest) / (lthr - hr_rest)
    hr_reserve_ratio = max(0.0, min(hr_reserve_ratio, 1.5))   # clamp

    # TRIMP with exponential weighting (gender-neutral ~1.67)
    trimp = (duration_seconds / 60) * hr_reserve_ratio * 0.64 * (2.718 ** (1.92 * hr_reserve_ratio))

    # Scale TRIMP to approximate TSS (1 hr at LTHR ≈ 100 TSS)
    trimp_at_lthr_1hr = 60 * 1.0 * 0.64 * (2.718 ** 1.92)   # ≈ 73
    tss_per_trimp = 100 / trimp_at_lthr_1hr
    return trimp * tss_per_trimp


# ─── Main sync ────────────────────────────────────────────────────────────────

async def sync_strava():
    if not strava_client.is_configured():
        logger.warning("Strava not configured — skipping. Run scripts/strava_auth.sh first.")
        return

    # Find the timestamp of the last synced Strava activity
    async with AsyncSessionLocal() as session:
        last = await session.scalar(
            select(Activity)
            .where(Activity.source == "strava")
            .order_by(Activity.start_time.desc())
            .limit(1)
        )
        after_ts = int(last.start_time.timestamp()) + 1 if last else 0

        # Load user profile for TSS calculations
        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))
        ftp = profile.ftp_watts if profile else None
        lthr = profile.lthr_bpm if profile else None

    try:
        activities = await strava_client.list_all_activities_since(after_ts)
    except Exception as e:
        logger.error(f"Strava activity fetch failed: {e}")
        return

    if not activities:
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        for act in activities:
            source_id = f"strava_{act['id']}"
            exists = await session.scalar(
                select(Activity).where(Activity.source_id == source_id)
            )
            if exists:
                continue

            start_str = act.get("start_date", "")
            try:
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                start_time = datetime.utcnow()

            duration = act.get("moving_time", 0) or act.get("elapsed_time", 0)
            avg_hr = act.get("average_heartrate")
            np_watts = act.get("weighted_average_watts")
            avg_watts = act.get("average_watts")

            # Compute TSS
            tss = None
            if np_watts and ftp:
                tss = compute_tss_from_power(duration, np_watts, ftp)
            elif avg_watts and ftp:
                tss = compute_tss_from_power(duration, avg_watts, ftp)
            elif avg_hr and lthr:
                tss = compute_tss_from_hr(duration, int(avg_hr), lthr)

            activity = Activity(
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
            )
            session.add(activity)
            new_count += 1

        await session.commit()
        if new_count:
            logger.info(f"Strava: stored {new_count} new activities")
