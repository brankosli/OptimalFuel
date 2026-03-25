"""
Activity deduplication + merge service.

Handles two types of duplicates:

1. Polar exercise vs Strava — mark Polar as polar_dedup, keep Strava

2. Strava vs Strava — two devices (e.g. Polar + Garmin) both synced to Strava
   Merge strategy:
   - PRIMARY = longer duration (captured more of the ride including warm-up)
   - SECONDARY = shorter one, stripped for missing fields only
   - HR: copied from secondary if primary lacks it
   - Power: keep primary's power (it recorded more of the ride)
   - Distance/elevation: take larger value
   - Duration: keep primary (longer)
   - TSS: recalculated with merged data

Match criteria:
   - Same sport type
   - Start times within 10 minutes (UTC normalized)
   - Duration within 20 minutes of each other
"""
from datetime import timedelta, timezone
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, UserProfile

POLAR_STRAVA_WINDOW  = timedelta(minutes=90)
STRAVA_STRAVA_WINDOW = timedelta(minutes=10)
MAX_DURATION_DIFF    = timedelta(minutes=20)


def _to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _merge_into_primary(primary: Activity, secondary: Activity, lthr=None, ftp=None):
    """
    Primary = longer duration (the accurate base).
    Secondary = shorter, used only to fill missing fields.

    Rules:
    - HR: take from secondary if primary lacks it
    - Power: keep primary's (it recorded more of the ride)
    - Distance/elevation/calories: take larger value
    - Duration: keep primary (already longer)
    - TSS: recalculate with merged HR + power
    """
    # HR from secondary if primary doesn't have it
    if not primary.avg_heart_rate and secondary.avg_heart_rate:
        primary.avg_heart_rate = secondary.avg_heart_rate
        print(f"    → Copied avg HR {secondary.avg_heart_rate} bpm from secondary")

    if not primary.max_heart_rate and secondary.max_heart_rate:
        primary.max_heart_rate = secondary.max_heart_rate

    # Distance — take larger
    if secondary.distance_meters and (
        not primary.distance_meters or
        secondary.distance_meters > primary.distance_meters
    ):
        primary.distance_meters = secondary.distance_meters

    # Elevation — take larger
    if secondary.elevation_gain_meters and (
        not primary.elevation_gain_meters or
        secondary.elevation_gain_meters > primary.elevation_gain_meters
    ):
        primary.elevation_gain_meters = secondary.elevation_gain_meters

    # Calories — take larger
    if secondary.calories and (
        not primary.calories or secondary.calories > primary.calories
    ):
        primary.calories = secondary.calories

    # Recalculate TSS with merged HR + power
    from app.services.strava.sync import _calc_tss
    new_tss = _calc_tss(
        primary.duration_seconds,
        primary.avg_heart_rate,
        primary.normalized_power_watts,
        primary.avg_power_watts,
        ftp or primary.ftp_watts,
        lthr,
    )
    if new_tss:
        primary.tss = round(new_tss, 1)


async def dedup_activities():
    async with AsyncSessionLocal() as session:
        all_acts = list(await session.scalars(
            select(Activity).order_by(Activity.activity_date, Activity.start_time)
        ))

        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))
        ftp  = profile.ftp_watts if profile else None
        lthr = profile.lthr_bpm if profile else None

        strava_acts = [a for a in all_acts if a.source == "strava"]
        polar_acts  = [a for a in all_acts if a.source == "polar"]

        print(f"Dedup: {len(strava_acts)} Strava, {len(polar_acts)} Polar activities")

        polar_dedup_count  = 0
        strava_dedup_count = 0

        # ── Step 1: Polar exercise → Strava duplicates ────────────────────────
        if polar_acts and strava_acts:
            strava_utc_index = [(a, _to_utc(a.start_time)) for a in strava_acts]
            for polar_act in polar_acts:
                polar_time = _to_utc(polar_act.start_time)
                if not polar_time:
                    continue
                for strava_act, s_time in strava_utc_index:
                    if s_time and abs(polar_time - s_time) <= POLAR_STRAVA_WINDOW:
                        polar_act.source = "polar_dedup"
                        polar_dedup_count += 1
                        break

        # ── Step 2: Strava vs Strava (two devices) ────────────────────────────
        active_strava = [a for a in strava_acts]
        processed = set()

        for i, act_a in enumerate(active_strava):
            if act_a.id in processed:
                continue

            time_a = _to_utc(act_a.start_time)
            if not time_a:
                continue

            for act_b in active_strava[i + 1:]:
                if act_b.id in processed:
                    continue
                if act_b.sport_type != act_a.sport_type:
                    continue

                time_b = _to_utc(act_b.start_time)
                if not time_b:
                    continue

                time_diff     = abs(time_a - time_b)
                duration_diff = abs(timedelta(seconds=(act_a.duration_seconds or 0) - (act_b.duration_seconds or 0)))

                if time_diff <= STRAVA_STRAVA_WINDOW and duration_diff <= MAX_DURATION_DIFF:
                    # Primary = longer duration (more accurate base)
                    if (act_a.duration_seconds or 0) >= (act_b.duration_seconds or 0):
                        primary, secondary = act_a, act_b
                    else:
                        primary, secondary = act_b, act_a

                    print(f"  Merging: '{primary.name}' {primary.duration_seconds//60}m "
                          f"(HR={primary.avg_heart_rate}, Power={primary.normalized_power_watts}W) "
                          f"← '{secondary.name}' {secondary.duration_seconds//60}m "
                          f"(HR={secondary.avg_heart_rate}, Power={secondary.normalized_power_watts}W)")

                    _merge_into_primary(primary, secondary, lthr=lthr, ftp=ftp)
                    secondary.source = "strava_dedup"
                    processed.add(secondary.id)
                    strava_dedup_count += 1

                    print(f"    Result: {primary.duration_seconds//60}m, "
                          f"HR={primary.avg_heart_rate}, "
                          f"Power={primary.normalized_power_watts}W, "
                          f"TSS={primary.tss}")
                    break

        await session.commit()

        total = polar_dedup_count + strava_dedup_count
        if total:
            print(f"Dedup: {polar_dedup_count} Polar + {strava_dedup_count} Strava duplicates resolved")
        else:
            print("Dedup: no duplicates found")
            if polar_acts and strava_acts:
                p, s = polar_acts[0], strava_acts[0]
                print(f"  Debug Polar:  {p.start_time} → UTC {_to_utc(p.start_time)}")
                print(f"  Debug Strava: {s.start_time} → UTC {_to_utc(s.start_time)}")