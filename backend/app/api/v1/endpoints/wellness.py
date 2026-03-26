"""
Wellness Log API.
Daily subjective check-in: energy, mood, soreness, sleep feeling, stress.
Each rated 1-5. Composite score = average × 20 (0-100 scale).

Scientific basis:
  Subjective wellness drops 2-3 weeks before HRV and performance metrics do.
  Foster et al. (1998) showed mood state is the earliest overtraining signal.
  Cross-correlating with TSS over time reveals your personal load tolerance ceiling.
"""
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import WellnessLog, DailySummary

router = APIRouter()


class WellnessCreate(BaseModel):
    log_date: str                    # YYYY-MM-DD
    energy:     Optional[int] = None  # 1-5
    mood:       Optional[int] = None
    soreness:   Optional[int] = None
    sleep_feel: Optional[int] = None
    stress:     Optional[int] = None
    notes:      Optional[str] = None


def _composite(energy, mood, soreness, sleep_feel, stress) -> float | None:
    vals = [v for v in [energy, mood, soreness, sleep_feel, stress] if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals) * 20, 1)


def _row_dict(w: WellnessLog) -> dict:
    return {
        "id":         w.id,
        "date":       w.log_date.isoformat(),
        "energy":     w.energy,
        "mood":       w.mood,
        "soreness":   w.soreness,
        "sleep_feel": w.sleep_feel,
        "stress":     w.stress,
        "composite":  w.composite,
        "notes":      w.notes,
    }


@router.get("/")
async def list_wellness(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date:   Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    end   = dt.date.today()
    start = end - dt.timedelta(days=30)
    if from_date:
        try: start = dt.date.fromisoformat(from_date)
        except ValueError: pass
    if to_date:
        try: end = dt.date.fromisoformat(to_date)
        except ValueError: pass

    rows = list(await db.scalars(
        select(WellnessLog)
        .where(WellnessLog.log_date >= start, WellnessLog.log_date <= end)
        .order_by(WellnessLog.log_date)
    ))
    return [_row_dict(w) for w in rows]


@router.get("/today")
async def today_wellness(db: AsyncSession = Depends(get_db)):
    today = dt.date.today()
    row   = await db.scalar(select(WellnessLog).where(WellnessLog.log_date == today))
    if not row:
        return None
    return _row_dict(row)


@router.post("/", status_code=201)
async def log_wellness(body: WellnessCreate, db: AsyncSession = Depends(get_db)):
    try:
        log_date = dt.date.fromisoformat(body.log_date)
    except ValueError:
        raise HTTPException(400, "Invalid date — use YYYY-MM-DD")

    # Validate 1-5 range
    for field, val in [("energy", body.energy), ("mood", body.mood),
                        ("soreness", body.soreness), ("sleep_feel", body.sleep_feel),
                        ("stress", body.stress)]:
        if val is not None and not (1 <= val <= 5):
            raise HTTPException(400, f"{field} must be between 1 and 5")

    composite = _composite(body.energy, body.mood, body.soreness,
                            body.sleep_feel, body.stress)

    # Upsert — one entry per day
    existing = await db.scalar(select(WellnessLog).where(WellnessLog.log_date == log_date))
    if existing:
        existing.energy     = body.energy
        existing.mood       = body.mood
        existing.soreness   = body.soreness
        existing.sleep_feel = body.sleep_feel
        existing.stress     = body.stress
        existing.composite  = composite
        existing.notes      = body.notes
        await db.commit()
        await db.refresh(existing)
        return _row_dict(existing)
    else:
        row = WellnessLog(
            log_date    = log_date,
            energy      = body.energy,
            mood        = body.mood,
            soreness    = body.soreness,
            sleep_feel  = body.sleep_feel,
            stress      = body.stress,
            composite   = composite,
            notes       = body.notes,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return _row_dict(row)


@router.delete("/{log_date}", status_code=204)
async def delete_wellness(log_date: str, db: AsyncSession = Depends(get_db)):
    try:
        d = dt.date.fromisoformat(log_date)
    except ValueError:
        raise HTTPException(400, "Invalid date")
    row = await db.scalar(select(WellnessLog).where(WellnessLog.log_date == d))
    if not row:
        raise HTTPException(404, "No entry for this date")
    await db.delete(row)
    await db.commit()


@router.get("/correlation")
async def wellness_tss_correlation(
    days: int = Query(60, ge=14, le=180),
    db: AsyncSession = Depends(get_db),
):
    """
    Return paired wellness + TSS data for correlation analysis.
    Shows how training load relates to next-day wellness.
    Used to find personal overtraining threshold.
    """
    end   = dt.date.today()
    start = end - dt.timedelta(days=days)

    wellness_rows = list(await db.scalars(
        select(WellnessLog)
        .where(WellnessLog.log_date >= start)
        .order_by(WellnessLog.log_date)
    ))
    summary_rows = list(await db.scalars(
        select(DailySummary)
        .where(DailySummary.summary_date >= start)
        .order_by(DailySummary.summary_date)
    ))

    tss_by_date = {s.summary_date: s.total_tss for s in summary_rows}
    atl_by_date = {s.summary_date: s.atl for s in summary_rows}

    points = []
    for w in wellness_rows:
        # Pair today's wellness with yesterday's TSS (load → next day feeling)
        prev = w.log_date - dt.timedelta(days=1)
        points.append({
            "date":          w.log_date.isoformat(),
            "composite":     w.composite,
            "energy":        w.energy,
            "mood":          w.mood,
            "soreness":      w.soreness,
            "prev_day_tss":  tss_by_date.get(prev),
            "atl":           atl_by_date.get(w.log_date),
        })

    return {"points": points, "days": days}
