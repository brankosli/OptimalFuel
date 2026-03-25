import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import DailySummary, SleepRecord, Activity, UserProfile

router = APIRouter()


@router.get("/")
async def list_summaries(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    end = dt.date.today()
    start = end - dt.timedelta(days=90)
    if from_date:
        try: start = dt.date.fromisoformat(from_date)
        except ValueError: pass
    if to_date:
        try: end = dt.date.fromisoformat(to_date)
        except ValueError: pass

    rows = list(await db.scalars(
        select(DailySummary)
        .where(DailySummary.summary_date >= start, DailySummary.summary_date <= end)
        .order_by(DailySummary.summary_date)
    ))
    return [_summary_dict(s) for s in rows]


@router.get("/today")
async def today_summary(db: AsyncSession = Depends(get_db)):
    today = dt.date.today()
    row = await db.scalar(select(DailySummary).where(DailySummary.summary_date == today))
    if not row:
        return {"message": "No data yet — trigger a sync first", "date": today.isoformat()}

    base = _summary_dict(row)

    # ── Generate rich recommendation ───────────────────────────────────────
    try:
        from app.services.analytics.recommendation import generate_recommendation

        # Load profile for LTHR
        profile = await db.scalar(select(UserProfile).where(UserProfile.id == 1))
        lthr = profile.lthr_bpm if profile else None

        # Last 7 days of activities for sport suggestion
        week_ago = today - dt.timedelta(days=7)
        recent_acts = list(await db.scalars(
            select(Activity)
            .where(
                Activity.activity_date >= week_ago,
                Activity.source.notin_(["polar_dedup", "strava_dedup"]),
            )
            .order_by(Activity.activity_date)
        ))
        recent_sports = [a.sport_type for a in recent_acts]

        # Last 7 nights of sleep quality for consecutive poor sleep detection
        sleep_rows = list(await db.scalars(
            select(SleepRecord)
            .where(SleepRecord.sleep_date >= week_ago, SleepRecord.sleep_date < today)
            .order_by(SleepRecord.sleep_date)
        ))
        sq_history = [s.sleep_quality_composite for s in sleep_rows]

        rec = generate_recommendation(
            tsb=row.tsb,
            atl=row.atl,
            ctl=row.ctl,
            acwr=row.acwr,
            sleep_quality=row.sleep_quality_composite,
            sleep_debt_minutes=row.sleep_debt_minutes,
            nocturnal_hr_dip=row.nocturnal_hr_dip,
            deep_sleep_deficit=row.deep_sleep_deficit,
            training_monotony=row.training_monotony,
            recovery_classification=row.recovery_classification,
            lthr=lthr,
            recent_sports=recent_sports,
            sleep_quality_history=sq_history,
        )
        base["recommendation"] = rec

    except Exception as e:
        base["recommendation"] = {"error": str(e)}

    return base


@router.get("/sleep-insights")
async def sleep_insights(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    end = dt.date.today()
    start = end - dt.timedelta(days=30)
    if from_date:
        try: start = dt.date.fromisoformat(from_date)
        except ValueError: pass
    if to_date:
        try: end = dt.date.fromisoformat(to_date)
        except ValueError: pass

    rows = list(await db.scalars(
        select(SleepRecord)
        .where(SleepRecord.sleep_date >= start, SleepRecord.sleep_date <= end)
        .order_by(SleepRecord.sleep_date)
    ))

    records = [{
        "date":                    s.sleep_date.isoformat(),
        "sleep_score":             s.sleep_score,
        "sleep_quality_composite": s.sleep_quality_composite,
        "total_hours":             round(s.total_sleep_seconds / 3600, 2) if s.total_sleep_seconds else None,
        "deep_pct":                s.deep_pct,
        "rem_pct":                 s.rem_pct,
        "light_pct":               s.light_pct,
        "deep_sleep_deficit":      s.deep_sleep_deficit,
        "continuity":              s.continuity,
        "sleep_cycles":            s.sleep_cycles,
        "resting_hr":              s.resting_hr,
        "nocturnal_hr_min":        s.nocturnal_hr_min,
        "nocturnal_hr_dip":        s.nocturnal_hr_dip,
        "sleep_charge":            s.sleep_charge,
        "total_interruption_min":  round(s.total_interruption_duration / 60) if s.total_interruption_duration else None,
    } for s in rows]

    avg_quality  = _avg([r["sleep_quality_composite"] for r in records])
    avg_deep     = _avg([r["deep_pct"] for r in records])
    avg_rem      = _avg([r["rem_pct"] for r in records])
    avg_hours    = _avg([r["total_hours"] for r in records if r["total_hours"]])
    avg_hr_dip   = _avg([r["nocturnal_hr_dip"] for r in records])
    deficit_days = sum(1 for r in records if r["deep_sleep_deficit"])

    return {
        "records": records,
        "aggregates": {
            "avg_quality_score":    round(avg_quality, 1) if avg_quality else None,
            "avg_deep_pct":         round(avg_deep, 1) if avg_deep else None,
            "avg_rem_pct":          round(avg_rem, 1) if avg_rem else None,
            "avg_hours":            round(avg_hours, 1) if avg_hours else None,
            "avg_nocturnal_hr_dip": round(avg_hr_dip, 1) if avg_hr_dip else None,
            "deep_deficit_days":    deficit_days,
            "deep_deficit_pct":     round(deficit_days / len(records) * 100) if records else 0,
        }
    }


@router.post("/sync")
async def trigger_sync():
    from app.tasks.scheduler import sync_all
    await sync_all()
    return {"message": "Sync complete"}


@router.get("/debug/polar-sleep-raw")
async def debug_polar_sleep_raw():
    from app.services.polar.client import polar_client
    nights = await polar_client.get_sleep()
    if nights:
        return {"count": len(nights), "first_record": nights[0]}
    return {"count": 0, "first_record": None}

@router.get("/debug/polar-check")
async def debug_polar_check():
    from app.core.config import settings
    return {
        "has_token":     bool(settings.polar_access_token),
        "has_user_id":   bool(settings.polar_user_id),
        "token_preview": settings.polar_access_token[:10] + "..." if settings.polar_access_token else None,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _summary_dict(s: DailySummary) -> dict:
    return {
        "date":                    s.summary_date.isoformat(),
        "ctl":                     s.ctl,
        "atl":                     s.atl,
        "tsb":                     s.tsb,
        "total_tss":               s.total_tss,
        "recovery_score":          s.recovery_score,
        "readiness_label":         s.readiness_label,
        "recovery_classification": s.recovery_classification,
        "training_recommendation": s.training_recommendation,
        "acwr":                    s.acwr,
        "training_monotony":       s.training_monotony,
        "training_strain":         s.training_strain,
        "sleep_quality_composite": s.sleep_quality_composite,
        "nocturnal_hr_dip":        s.nocturnal_hr_dip,
        "deep_sleep_deficit":      s.deep_sleep_deficit,
        "sleep_debt_minutes":      s.sleep_debt_minutes,
        "target_calories":         s.target_calories,
        "target_carbs_g":          s.target_carbs_g,
        "target_protein_g":        s.target_protein_g,
        "target_fat_g":            s.target_fat_g,
        "carb_strategy":           s.carb_strategy,
        "total_calories_burned":   s.total_calories_burned,
        "total_activity_seconds":  s.total_activity_seconds,
    }

def _avg(values):
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None


@router.get("/weekly-report")
async def weekly_report(
    week_offset: int = Query(0, description="0 = current week, -1 = last week, etc."),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate weekly training report for any given week.
    week_offset=0 → current week (Mon–Sun)
    week_offset=-1 → last week
    """
    from app.services.analytics.weekly_report import generate_weekly_report

    today = dt.date.today()
    # Find Monday of the target week
    days_since_monday = today.weekday()
    this_monday = today - dt.timedelta(days=days_since_monday)
    week_start = this_monday + dt.timedelta(weeks=week_offset)
    week_end   = week_start + dt.timedelta(days=6)

    prev_start = week_start - dt.timedelta(weeks=1)
    prev_end   = prev_start + dt.timedelta(days=6)

    # Load DailySummary rows
    week_rows = list(await db.scalars(
        select(DailySummary)
        .where(DailySummary.summary_date >= week_start,
               DailySummary.summary_date <= week_end)
        .order_by(DailySummary.summary_date)
    ))
    prev_rows = list(await db.scalars(
        select(DailySummary)
        .where(DailySummary.summary_date >= prev_start,
               DailySummary.summary_date <= prev_end)
        .order_by(DailySummary.summary_date)
    ))

    # Load activities for the week
    week_acts = list(await db.scalars(
        select(Activity)
        .where(
            Activity.activity_date >= week_start,
            Activity.activity_date <= week_end,
            Activity.source.notin_(["polar_dedup", "strava_dedup"]),
        )
        .order_by(Activity.activity_date)
    ))

    # Load sleep for the week
    week_sleep = list(await db.scalars(
        select(SleepRecord)
        .where(SleepRecord.sleep_date >= week_start,
               SleepRecord.sleep_date <= week_end)
        .order_by(SleepRecord.sleep_date)
    ))

    # Load profile
    profile = await db.scalar(select(UserProfile).where(UserProfile.id == 1))

    def summary_to_dict(s):
        return {
            "total_tss":          s.total_tss,
            "ctl":                s.ctl,
            "atl":                s.atl,
            "tsb":                s.tsb,
            "acwr":               s.acwr,
            "training_monotony":  s.training_monotony,
            "sleep_quality_composite": s.sleep_quality_composite,
            "sleep_debt_minutes": s.sleep_debt_minutes,
        }

    def act_to_dict(a):
        return {
            "sport_type":       a.sport_type,
            "duration_seconds": a.duration_seconds,
            "tss":              a.tss,
            "avg_heart_rate":   a.avg_heart_rate,
        }

    def sleep_to_dict(s):
        return {
            "sleep_quality_composite": s.sleep_quality_composite,
            "total_sleep_seconds":     s.total_sleep_seconds,
            "deep_sleep_deficit":      s.deep_sleep_deficit,
            "nocturnal_hr_dip":        s.nocturnal_hr_dip,
        }

    report = generate_weekly_report(
        week_summaries  = [summary_to_dict(s) for s in week_rows],
        prev_summaries  = [summary_to_dict(s) for s in prev_rows],
        week_activities = [act_to_dict(a) for a in week_acts],
        week_sleep      = [sleep_to_dict(s) for s in week_sleep],
        week_start      = week_start,
        week_end        = week_end,
        lthr            = profile.lthr_bpm if profile else None,
        ftp             = profile.ftp_watts if profile else None,
    )

    return report
