from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import MealLog

router = APIRouter()


class MealCreate(BaseModel):
    log_date: str
    meal_type: str
    name: str
    calories: Optional[float] = None
    carbs_g: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    notes: Optional[str] = None


@router.get("/meals")
async def get_meals(log_date: str, db: AsyncSession = Depends(get_db)):
    try:
        d = date.fromisoformat(log_date)
    except ValueError:
        raise HTTPException(400, "Invalid date format — use YYYY-MM-DD")

    rows = list(await db.scalars(
        select(MealLog).where(MealLog.log_date == d).order_by(MealLog.created_at)
    ))
    return [
        {"id": m.id, "meal_type": m.meal_type, "name": m.name,
         "calories": m.calories, "carbs_g": m.carbs_g,
         "protein_g": m.protein_g, "fat_g": m.fat_g, "notes": m.notes}
        for m in rows
    ]


@router.post("/meals", status_code=201)
async def log_meal(meal: MealCreate, db: AsyncSession = Depends(get_db)):
    try:
        d = date.fromisoformat(meal.log_date)
    except ValueError:
        raise HTTPException(400, "Invalid date")

    record = MealLog(
        log_date=d, meal_type=meal.meal_type, name=meal.name,
        calories=meal.calories, carbs_g=meal.carbs_g,
        protein_g=meal.protein_g, fat_g=meal.fat_g, notes=meal.notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"id": record.id, "message": "Meal logged"}


@router.delete("/meals/{meal_id}")
async def delete_meal(meal_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.scalar(select(MealLog).where(MealLog.id == meal_id))
    if not row:
        raise HTTPException(404, "Meal not found")
    await db.delete(row)
    await db.commit()
    return {"message": "Deleted"}
