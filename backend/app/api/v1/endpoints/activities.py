from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import Activity

router = APIRouter()


@router.get("/")
async def list_activities(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    sport: Optional[str] = None,
    limit: int = Query(50, le=200),
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

    q = select(Activity).where(
        Activity.activity_date >= start, Activity.activity_date <= end
    )
    if sport:
        q = q.where(Activity.sport_type == sport)
    q = q.order_by(Activity.start_time.desc()).limit(limit)

    rows = list(await db.scalars(q))
    return [
        {"id": a.id, "source": a.source, "date": a.activity_date.isoformat(),
         "start_time": a.start_time.isoformat(), "sport_type": a.sport_type,
         "name": a.name, "duration_seconds": a.duration_seconds,
         "calories": a.calories, "distance_meters": a.distance_meters,
         "avg_heart_rate": a.avg_heart_rate, "max_heart_rate": a.max_heart_rate,
         "tss": a.tss, "training_load": a.training_load,
         "avg_power_watts": a.avg_power_watts, "elevation_gain_meters": a.elevation_gain_meters}
        for a in rows
    ]
