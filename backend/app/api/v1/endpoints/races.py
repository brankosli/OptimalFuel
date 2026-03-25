"""
Race Calendar API.
CRUD for races + periodisation plan computed on the fly.
"""
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import Race, DailySummary, Activity

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RaceCreate(BaseModel):
    name: str
    race_date: str                       # YYYY-MM-DD
    race_type: str                       # marathon | half_marathon | 10k | 5k | cycling | other
    priority: str = "A"                  # A | B | C | test
    target_finish_time: Optional[str] = None
    notes: Optional[str] = None
    override_base_tss: Optional[int] = None
    override_build_tss: Optional[int] = None
    override_peak_tss: Optional[int] = None


class RaceUpdate(RaceCreate):
    actual_finish_time: Optional[str] = None
    completed: Optional[bool] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_races(db: AsyncSession = Depends(get_db)):
    rows = list(await db.scalars(
        select(Race).order_by(Race.race_date)
    ))
    today = dt.date.today()

    result = []
    for r in rows:
        plan = await _get_plan(r, db, today)
        result.append({**_race_dict(r), "plan": plan})
    return result


@router.post("/", status_code=201)
async def create_race(body: RaceCreate, db: AsyncSession = Depends(get_db)):
    try:
        race_date = dt.date.fromisoformat(body.race_date)
    except ValueError:
        raise HTTPException(400, "Invalid date format — use YYYY-MM-DD")

    race = Race(
        name=body.name,
        race_date=race_date,
        race_type=body.race_type,
        priority=body.priority,
        target_finish_time=body.target_finish_time,
        notes=body.notes,
        override_base_tss=body.override_base_tss,
        override_build_tss=body.override_build_tss,
        override_peak_tss=body.override_peak_tss,
    )
    db.add(race)
    await db.commit()
    await db.refresh(race)

    today = dt.date.today()
    plan  = await _get_plan(race, db, today)
    return {**_race_dict(race), "plan": plan}


@router.get("/{race_id}")
async def get_race(race_id: int, db: AsyncSession = Depends(get_db)):
    race = await _fetch_or_404(race_id, db)
    today = dt.date.today()
    plan  = await _get_plan(race, db, today)
    return {**_race_dict(race), "plan": plan}


@router.put("/{race_id}")
async def update_race(race_id: int, body: RaceUpdate, db: AsyncSession = Depends(get_db)):
    race = await _fetch_or_404(race_id, db)

    try:
        race.race_date = dt.date.fromisoformat(body.race_date)
    except ValueError:
        raise HTTPException(400, "Invalid date")

    race.name               = body.name
    race.race_type          = body.race_type
    race.priority           = body.priority
    race.target_finish_time = body.target_finish_time
    race.actual_finish_time = body.actual_finish_time
    race.notes              = body.notes
    race.completed          = body.completed or False
    race.override_base_tss  = body.override_base_tss
    race.override_build_tss = body.override_build_tss
    race.override_peak_tss  = body.override_peak_tss

    await db.commit()
    await db.refresh(race)

    today = dt.date.today()
    plan  = await _get_plan(race, db, today)
    return {**_race_dict(race), "plan": plan}


@router.delete("/{race_id}", status_code=204)
async def delete_race(race_id: int, db: AsyncSession = Depends(get_db)):
    race = await _fetch_or_404(race_id, db)
    await db.delete(race)
    await db.commit()


@router.get("/dashboard/next")
async def next_race(db: AsyncSession = Depends(get_db)):
    """
    Returns the next upcoming A race with its plan.
    Used by the dashboard banner.
    """
    today = dt.date.today()
    race  = await db.scalar(
        select(Race)
        .where(Race.race_date >= today, Race.priority == "A", Race.completed == False)
        .order_by(Race.race_date)
        .limit(1)
    )
    if not race:
        # Fall back to any upcoming race
        race = await db.scalar(
            select(Race)
            .where(Race.race_date >= today, Race.completed == False)
            .order_by(Race.race_date)
            .limit(1)
        )
    if not race:
        return None

    plan = await _get_plan(race, db, today)
    return {**_race_dict(race), "plan": plan}


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _fetch_or_404(race_id: int, db: AsyncSession) -> Race:
    race = await db.scalar(select(Race).where(Race.id == race_id))
    if not race:
        raise HTTPException(404, "Race not found")
    return race


async def _get_plan(race: Race, db: AsyncSession, today: dt.date) -> dict:
    """Compute periodisation plan for a race using current athlete state."""
    from app.services.analytics.periodisation import analyse_race

    # Get latest DailySummary for CTL/ATL/TSB
    summary = await db.scalar(
        select(DailySummary)
        .where(DailySummary.summary_date <= today)
        .order_by(DailySummary.summary_date.desc())
        .limit(1)
    )
    ctl = summary.ctl or 0.0 if summary else 0.0
    atl = summary.atl or 0.0 if summary else 0.0
    tsb = summary.tsb or 0.0 if summary else 0.0

    # 4-week average weekly TSS
    four_weeks_ago = today - dt.timedelta(weeks=4)
    recent = list(await db.scalars(
        select(DailySummary)
        .where(DailySummary.summary_date >= four_weeks_ago,
               DailySummary.summary_date <= today)
    ))
    if recent:
        total_tss = sum((s.total_tss or 0) for s in recent)
        avg_weekly_tss = total_tss / 4
    else:
        avg_weekly_tss = 0.0

    return analyse_race(
        race_date         = race.race_date,
        race_type         = race.race_type,
        priority          = race.priority,
        current_ctl       = ctl,
        current_atl       = atl,
        current_tsb       = tsb,
        avg_weekly_tss    = avg_weekly_tss,
        today             = today,
        override_base_tss = race.override_base_tss,
        override_build_tss= race.override_build_tss,
        override_peak_tss = race.override_peak_tss,
    )


def _race_dict(r: Race) -> dict:
    return {
        "id":                  r.id,
        "name":                r.name,
        "race_date":           r.race_date.isoformat(),
        "race_type":           r.race_type,
        "priority":            r.priority,
        "target_finish_time":  r.target_finish_time,
        "actual_finish_time":  r.actual_finish_time,
        "notes":               r.notes,
        "completed":           r.completed,
        "override_base_tss":   r.override_base_tss,
        "override_build_tss":  r.override_build_tss,
        "override_peak_tss":   r.override_peak_tss,
    }
