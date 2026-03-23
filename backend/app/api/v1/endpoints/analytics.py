from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import DailySummary

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
    return [
        {"date": s.summary_date.isoformat(), "ctl": s.ctl, "atl": s.atl, "tsb": s.tsb,
         "total_tss": s.total_tss, "recovery_score": s.recovery_score,
         "readiness_label": s.readiness_label, "target_calories": s.target_calories,
         "target_carbs_g": s.target_carbs_g, "target_protein_g": s.target_protein_g,
         "target_fat_g": s.target_fat_g, "carb_strategy": s.carb_strategy}
        for s in rows
    ]


@router.get("/today")
async def today_summary(db: AsyncSession = Depends(get_db)):
    today = date.today()
    row = await db.scalar(select(DailySummary).where(DailySummary.summary_date == today))
    if not row:
        return {"message": "No data yet — trigger a sync first", "date": today.isoformat()}
    return {
        "date": row.summary_date.isoformat(), "ctl": row.ctl, "atl": row.atl, "tsb": row.tsb,
        "total_tss": row.total_tss, "recovery_score": row.recovery_score,
        "readiness_label": row.readiness_label, "target_calories": row.target_calories,
        "target_carbs_g": row.target_carbs_g, "target_protein_g": row.target_protein_g,
        "target_fat_g": row.target_fat_g, "carb_strategy": row.carb_strategy,
        "total_calories_burned": row.total_calories_burned,
        "total_activity_seconds": row.total_activity_seconds,
    }


@router.post("/sync")
async def trigger_sync():
    """Manually kick off a full sync + analytics recompute."""
    import asyncio
    from app.tasks.scheduler import sync_all
    asyncio.create_task(sync_all())
    return {"message": "Sync started in background"}


@router.get("/debug/polar-sleep")
async def debug_polar_sleep():
    from app.services.polar.client import polar_client
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://www.polaraccesslink.com/v3/users/sleep",  # no user-id!
            headers=polar_client._headers(),
        )
        return {"status_code": r.status_code, "body": r.text}