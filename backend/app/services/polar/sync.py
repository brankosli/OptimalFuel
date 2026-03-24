"""
Polar sync service.
Pulls exercises, sleep and user profile from Polar Accesslink.
Computes analytics on each sleep record before storing.
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
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?"
    m = re.match(pattern, iso_duration or "PT0S")
    if not m:
        return 0
    return int(int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0))


def _map_sport(polar_sport: str) -> str:
    mapping = {
        "RUNNING": "run", "CYCLING": "ride", "SWIMMING": "swim",
        "STRENGTH_TRAINING": "strength", "HIKING": "hike",
        "ROWING": "rowing", "YOGA": "yoga", "CROSS_TRAINING": "crosstraining",
    }
    return mapping.get((polar_sport or "").upper(), (polar_sport or "other").lower())


# ─── Sleep analytics ──────────────────────────────────────────────────────────

def _compute_sleep_quality(
    total_s: int,
    deep_s: int,
    rem_s: int,
    continuity: float | None,
) -> float | None:
    if not total_s or total_s < 3600:
        return None

    deep_pct = deep_s / total_s if total_s else 0
    deep_score = min(deep_pct / 0.20 * 100, 100)

    rem_pct = rem_s / total_s if total_s else 0
    rem_score = min(rem_pct / 0.25 * 100, 100)

    hours = total_s / 3600
    if hours >= 7:
        duration_score = 100 if hours <= 9 else max(60, 100 - (hours - 9) * 20)
    elif hours >= 6:
        duration_score = 70
    elif hours >= 5:
        duration_score = 40
    else:
        duration_score = 10

    cont = continuity if continuity is not None else 2.5
    continuity_score = (cont / 5.0) * 100

    composite = (
        deep_score       * 0.35 +
        rem_score        * 0.20 +
        continuity_score * 0.25 +
        duration_score   * 0.20
    )
    return round(composite, 1)


def _compute_nocturnal_hr_dip(
    hr_samples: dict | None,
    resting_hr: int | None,
) -> tuple[int | None, float | None]:
    if not hr_samples or not resting_hr or resting_hr <= 0:
        return None, None
    values = [v for v in hr_samples.values() if isinstance(v, (int, float)) and v > 20]
    if not values:
        return None, None
    min_hr = int(min(values))
    dip = (resting_hr - min_hr) / resting_hr * 100
    return min_hr, round(dip, 1)


def _avg_hr_from_samples(samples: dict | None) -> int | None:
    if not samples:
        return None
    values = [v for v in samples.values() if isinstance(v, (int, float)) and v > 20]
    if not values:
        return None
    return round(sum(values) / len(values))


# ─── Main sync ────────────────────────────────────────────────────────────────

async def sync_polar():
    if not polar_client.is_configured():
        print("Polar not configured — skipping")
        return
    await _sync_user_profile()
    await _sync_exercises()
    await _sync_sleep()


# ─── User profile ─────────────────────────────────────────────────────────────

async def _sync_user_profile():
    """
    Pull user info + physical info from Polar and populate UserProfile.
    Only fills empty fields — manual overrides in Settings are never overwritten.

    Sources:
    - get_user_info()     → weight, height, gender, birthdate
    - get_physical_info() → VO2max, LTHR (anaerobic threshold HR)

    FTP is not available from Polar — must be entered manually.
    """
    # ── Basic user info ───────────────────────────────────────────────────────
    try:
        info = await polar_client.get_user_info()
    except Exception as e:
        print(f"Polar user info fetch failed: {e}")
        return

    # ── Physical info (VO2max, LTHR) ─────────────────────────────────────────
    physical = None
    try:
        physical_list = await polar_client.get_physical_info()
        if physical_list:
            physical = physical_list[-1]   # most recent entry
            print(f"Polar: got physical info entry dated {physical.get('created', '?')}")
    except Exception as e:
        print(f"Polar physical info fetch failed (non-critical): {e}")

    from app.models.models import UserProfile

    async with AsyncSessionLocal() as session:
        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))
        if not profile:
            profile = UserProfile(id=1)
            session.add(profile)

        # ── From user info ────────────────────────────────────────────────────
        if not profile.weight_kg and info.get("weight"):
            profile.weight_kg = float(info["weight"])

        if not profile.height_cm and info.get("height"):
            profile.height_cm = float(info["height"])

        if not profile.sex and info.get("gender"):
            profile.sex = info["gender"].lower()   # Polar: "MALE" / "FEMALE"

        if not profile.age and info.get("birthdate"):
            try:
                born = date.fromisoformat(info["birthdate"])
                today = date.today()
                profile.age = today.year - born.year - (
                    (today.month, today.day) < (born.month, born.day)
                )
            except (ValueError, AttributeError):
                pass

        # ── From physical info ────────────────────────────────────────────────
        if physical:
            # VO2max
            if not profile.vo2max:
                vo2 = physical.get("vo2-max")
                if vo2:
                    try:
                        profile.vo2max = float(vo2)
                    except (TypeError, ValueError):
                        pass

            # LTHR — Polar stores as "anaerobic-threshold" heart rate
            if not profile.lthr_bpm:
                thresholds = physical.get("aerobic-and-anaerobic-thresholds")
                if thresholds:
                    anaerobic = thresholds.get("anaerobic-threshold", {})
                    hr = anaerobic.get("heart-rate") if isinstance(anaerobic, dict) else None
                    if hr:
                        try:
                            profile.lthr_bpm = int(hr)
                        except (TypeError, ValueError):
                            pass

        await session.commit()
        print(
            f"Polar: profile synced — "
            f"{info.get('first-name')} {info.get('last-name')} | "
            f"{profile.weight_kg}kg {profile.height_cm}cm "
            f"age {profile.age} {profile.sex} | "
            f"VO2max {profile.vo2max} LTHR {profile.lthr_bpm}bpm"
        )


# ─── Exercises ────────────────────────────────────────────────────────────────

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
            if await session.scalar(select(Activity).where(Activity.source_id == source_id)):
                continue

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


# ─── Sleep ────────────────────────────────────────────────────────────────────

async def _sync_sleep():
    try:
        nights = await polar_client.get_sleep()
    except Exception as e:
        print(f"Polar sleep fetch failed: {e}")
        return

    if not nights:
        print("Polar: no sleep records returned")
        return

    async with AsyncSessionLocal() as session:
        new_count = 0
        updated_count = 0

        for night in nights:
            date_str = night.get("date", "")
            try:
                sleep_date = date.fromisoformat(date_str)
            except (ValueError, AttributeError):
                continue

            source_id = f"polar_sleep_{date_str}"

            light  = night.get("light_sleep")
            deep   = night.get("deep_sleep")
            rem    = night.get("rem_sleep")
            unrec  = night.get("unrecognized_sleep_stage", 0) or 0
            total  = (light or 0) + (deep or 0) + (rem or 0) + unrec if any(
                v is not None for v in [light, deep, rem]) else None

            continuity       = night.get("continuity")
            continuity_class = night.get("continuity_class")
            sleep_cycles     = night.get("sleep_cycles")
            sleep_score      = night.get("sleep_score")
            sleep_charge     = night.get("sleep_charge")
            interruptions    = night.get("total_interruption_duration")

            bedtime = wake_time = None
            try:
                if night.get("sleep_start_time"):
                    bedtime = datetime.fromisoformat(night["sleep_start_time"])
                if night.get("sleep_end_time"):
                    wake_time = datetime.fromisoformat(night["sleep_end_time"])
            except (ValueError, AttributeError):
                pass

            resting_hr = _avg_hr_from_samples(night.get("heart_rate_samples"))
            nocturnal_min, hr_dip = _compute_nocturnal_hr_dip(
                night.get("heart_rate_samples"), resting_hr
            )

            deep_pct  = round(deep / total * 100, 1) if total and deep else None
            rem_pct   = round(rem / total * 100, 1) if total and rem else None
            light_pct = round(light / total * 100, 1) if total and light else None

            quality      = _compute_sleep_quality(total or 0, deep or 0, rem or 0, continuity)
            deep_deficit = (deep_pct < 15) if deep_pct is not None else None

            raw = {k: night[k] for k in (
                "date", "sleep_score", "light_sleep", "deep_sleep", "rem_sleep",
                "sleep_charge", "continuity", "sleep_cycles", "continuity_class"
            ) if k in night}

            existing = await session.scalar(
                select(SleepRecord).where(SleepRecord.source_id == source_id)
            )

            fields = dict(
                sleep_date=sleep_date,
                bedtime=bedtime,
                wake_time=wake_time,
                total_sleep_seconds=total,
                light_sleep_seconds=light,
                deep_sleep_seconds=deep,
                rem_sleep_seconds=rem,
                unrecognized_sleep_seconds=unrec,
                deep_pct=deep_pct,
                rem_pct=rem_pct,
                light_pct=light_pct,
                sleep_score=sleep_score,
                sleep_charge=sleep_charge,
                sleep_cycles=sleep_cycles,
                continuity=continuity,
                continuity_class=continuity_class,
                total_interruption_duration=interruptions,
                resting_hr=resting_hr,
                nocturnal_hr_min=nocturnal_min,
                nocturnal_hr_dip=hr_dip,
                sleep_quality_composite=quality,
                deep_sleep_deficit=deep_deficit,
                raw_data=raw,
            )

            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                updated_count += 1
            else:
                session.add(SleepRecord(source="polar", source_id=source_id, **fields))
                new_count += 1

        await session.commit()
        print(f"Polar: {new_count} new + {updated_count} updated sleep records")