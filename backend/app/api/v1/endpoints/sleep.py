from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import SleepRecord

router = APIRouter()


@router.get("/")
async def list_sleep(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
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
        .order_by(SleepRecord.sleep_date.desc())
    ))
    return [
        {"id": s.id, "date": s.sleep_date.isoformat(),
         "total_sleep_seconds": s.total_sleep_seconds,
         "deep_sleep_seconds": s.deep_sleep_seconds, "rem_sleep_seconds": s.rem_sleep_seconds,
         "light_sleep_seconds": s.light_sleep_seconds, "sleep_score": s.sleep_score,
         "nightly_recharge_score": s.nightly_recharge_score,
         "ans_charge": s.ans_charge, "sleep_charge": s.sleep_charge,
         "hrv_rmssd": s.hrv_rmssd, "resting_hr": s.resting_hr}
        for s in rows
    ]
