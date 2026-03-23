from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import UserProfile

router = APIRouter()


class ProfileUpdate(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    ftp_watts: Optional[float] = None
    lthr_bpm: Optional[int] = None
    vo2max: Optional[float] = None
    dietary_preference: Optional[str] = None
    protein_target_per_kg: Optional[float] = None


@router.get("/")
async def get_profile(db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(UserProfile).where(UserProfile.id == 1))
    if not profile:
        return {"message": "Profile not set up yet", "configured": False}
    return {
        "configured": True,
        "weight_kg": profile.weight_kg, "height_cm": profile.height_cm,
        "age": profile.age, "sex": profile.sex,
        "ftp_watts": profile.ftp_watts, "lthr_bpm": profile.lthr_bpm,
        "vo2max": profile.vo2max, "dietary_preference": profile.dietary_preference,
        "protein_target_per_kg": profile.protein_target_per_kg,
    }


@router.put("/")
async def update_profile(data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(UserProfile).where(UserProfile.id == 1))
    if not profile:
        profile = UserProfile(id=1)
        db.add(profile)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.commit()

    # Recompute nutrition targets with new profile data
    from app.services.analytics.pmc import recompute_daily_summaries
    import asyncio
    asyncio.create_task(recompute_daily_summaries())

    return {"message": "Profile updated — nutrition targets recalculating"}
