from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import DailySummary, SleepRecord

router = APIRouter()


@router.get("/")
async def list_summaries(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    end = date.today()
    start = end - timedelta(days=90)
    if from_date:
        try: start = date.fromisoformat(from_date)
        except ValueError: pass
    if to_date:
        try: end = date.fromisoformat(to_date)
        except ValueError: pass

    rows = list(await db.scalars(
        select(DailySummary)
        .where(DailySummary.summary_date >= start, DailySummary.summary_date <= end)
        .order_by(DailySummary.summary_date)
    ))
    return [_summary_dict(s) for s in rows]


@router.get("/today")
async def today_summary(db: AsyncSession = Depends(get_db)):
    today = date.today()
    row = await db.scalar(select(DailySummary).where(DailySummary.summary_date == today))
    if not row:
        return {"message": "No data yet — trigger a sync first", "date": today.isoformat()}
    return _summary_dict(row)


@router.get("/sleep-insights")
async def sleep_insights(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed sleep analytics — quality scores, stage %, HR dip trend, sleep debt.
    Used by the enhanced Sleep page.
    """
    end = date.today()
    start = end - timedelta(days=30)
    if from_date:
        try: start = date.fromisoformat(from_date)
        except ValueError: pass
    if to_date:
        try: end = date.fromisoformat(to_date)
        except ValueError: pass

    rows = list(await db.scalars(
        select(SleepRecord)
        .where(SleepRecord.sleep_date >= start, SleepRecord.sleep_date <= end)
        .order_by(SleepRecord.sleep_date)
    ))

    records = []
    for s in rows:
        records.append({
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
        })

    # Period aggregates
    valid = [r for r in records if r["total_hours"]]
    avg_quality = _avg([r["sleep_quality_composite"] for r in records])
    avg_deep    = _avg([r["deep_pct"] for r in records])
    avg_rem     = _avg([r["rem_pct"] for r in records])
    avg_hours   = _avg([r["total_hours"] for r in valid])
    avg_hr_dip  = _avg([r["nocturnal_hr_dip"] for r in records])
    deficit_days = sum(1 for r in records if r["deep_sleep_deficit"])

    return {
        "records": records,
        "aggregates": {
            "avg_quality_score":  round(avg_quality, 1) if avg_quality else None,
            "avg_deep_pct":       round(avg_deep, 1) if avg_deep else None,
            "avg_rem_pct":        round(avg_rem, 1) if avg_rem else None,
            "avg_hours":          round(avg_hours, 1) if avg_hours else None,
            "avg_nocturnal_hr_dip": round(avg_hr_dip, 1) if avg_hr_dip else None,
            "deep_deficit_days":  deficit_days,
            "deep_deficit_pct":   round(deficit_days / len(records) * 100) if records else 0,
        }
    }


@router.post("/sync")
async def trigger_sync():
    """Manually kick off a full sync + analytics recompute."""
    from app.tasks.scheduler import sync_all
    await sync_all()
    return {"message": "Sync complete"}


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
        "sleep_quality_composite": s.sleep_quality_composite,
        "nocturnal_hr_dip":        s.nocturnal_hr_dip,
        "deep_sleep_deficit":      s.deep_sleep_deficit,
        "sleep_debt_minutes":      s.sleep_debt_minutes,
        "recovery_classification": s.recovery_classification,
        "training_recommendation": s.training_recommendation,
        "target_calories":         s.target_calories,
        "target_carbs_g":          s.target_carbs_g,
        "target_protein_g":        s.target_protein_g,
        "target_fat_g":            s.target_fat_g,
        "carb_strategy":           s.carb_strategy,
        "acwr":                    s.acwr,
        "training_monotony":       s.training_monotony,
        "training_strain":         s.training_strain,
        "training_strain":         s.training_strain,
        "total_calories_burned":   s.total_calories_burned,
        "total_activity_seconds":  s.total_activity_seconds,
    }


def _avg(values: list) -> float | None:
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)
