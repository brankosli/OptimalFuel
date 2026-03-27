"""
Nutrition API endpoints.

Combines:
1. Meal log CRUD (existing)
2. Edamam food search — search foods, get nutritional data
3. AI meal recommendations — Claude-powered daily meal plan
   based on today's targets, training context and dietary preference
"""
import datetime
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import MealLog, UserProfile, DailySummary, Activity
from app.core.config import settings

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class MealCreate(BaseModel):
    log_date: str
    meal_type: str
    name: str
    calories: Optional[float] = None
    carbs_g: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    notes: Optional[str] = None


# ─── Meal log CRUD ────────────────────────────────────────────────────────────

@router.get("/meals")
async def get_meals(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    try:
        d = datetime.date.fromisoformat(date)
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
        d = datetime.date.fromisoformat(meal.log_date)
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


# ─── Edamam food search ───────────────────────────────────────────────────────

@router.get("/food-search")
async def food_search(
    q: str = Query(..., min_length=2, description="Food name to search"),
    limit: int = Query(8, ge=1, le=20),
):
    """
    Search Edamam food database.
    Returns foods with calories, macros per 100g and per serving.
    """
    app_id  = settings.edamam_app_id
    app_key = settings.edamam_app_key

    if not app_id or not app_key:
        raise HTTPException(503, "Edamam API not configured — add EDAMAM_APP_ID and EDAMAM_APP_KEY to .env")

    url = "https://api.edamam.com/api/food-database/v2/parser"
    params = {
        "app_id":  app_id,
        "app_key": app_key,
        "ingr":    q,
        "limit":   limit,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            raise HTTPException(502, f"Edamam error: {r.status_code}")
        data = r.json()

    results = []
    for hint in data.get("hints", [])[:limit]:
        food   = hint.get("food", {})
        nutrients = food.get("nutrients", {})

        # Build serving options from measures
        measures = []
        for m in hint.get("measures", [])[:4]:
            measures.append({
                "label":  m.get("label", "serving"),
                "weight": m.get("weight", 100),
            })

        results.append({
            "food_id":  food.get("foodId"),
            "label":    food.get("label"),
            "category": food.get("category"),
            "image":    food.get("image"),
            # Per 100g
            "per_100g": {
                "calories": round(nutrients.get("ENERC_KCAL", 0), 1),
                "carbs_g":  round(nutrients.get("CHOCDF", 0), 1),
                "protein_g":round(nutrients.get("PROCNT", 0), 1),
                "fat_g":    round(nutrients.get("FAT", 0), 1),
                "fiber_g":  round(nutrients.get("FIBTG", 0), 1),
            },
            "measures": measures,
        })

    return {"results": results, "query": q}


@router.get("/food-nutrients")
async def food_nutrients(
    food_id: str = Query(...),
    measure_uri: str = Query(...),
    quantity: float = Query(1.0),
):
    """
    Get exact nutrients for a food + measure combination.
    Used when user selects a specific serving size.
    """
    app_id  = settings.edamam_app_id
    app_key = settings.edamam_app_key

    if not app_id or not app_key:
        raise HTTPException(503, "Edamam API not configured")

    url  = "https://api.edamam.com/api/food-database/v2/nutrients"
    body = {
        "ingredients": [{
            "quantity":   quantity,
            "measureURI": measure_uri,
            "foodId":     food_id,
        }]
    }
    params = {"app_id": app_id, "app_key": app_key}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body, params=params)
        if r.status_code != 200:
            raise HTTPException(502, f"Edamam error: {r.status_code}")
        data = r.json()

    n = data.get("totalNutrients", {})
    return {
        "calories":  round(data.get("calories", 0), 1),
        "carbs_g":   round(n.get("CHOCDF", {}).get("quantity", 0), 1),
        "protein_g": round(n.get("PROCNT", {}).get("quantity", 0), 1),
        "fat_g":     round(n.get("FAT",    {}).get("quantity", 0), 1),
        "fiber_g":   round(n.get("FIBTG",  {}).get("quantity", 0), 1),
    }


# ─── AI meal recommendations ──────────────────────────────────────────────────

@router.get("/recommendations")
async def meal_recommendations(db: AsyncSession = Depends(get_db)):
    """
    Generate daily meal recommendations using Claude AI.
    Passes today's training context, targets and dietary preference.
    Returns structured meal suggestions with timing guidance.
    """
    today = datetime.date.today()

    # Load today's summary
    summary = await db.scalar(
        select(DailySummary).where(DailySummary.summary_date == today)
    )

    # Load profile
    profile = await db.scalar(select(UserProfile).where(UserProfile.id == 1))

    # Load today's activities
    activities = list(await db.scalars(
        select(Activity).where(
            Activity.activity_date == today,
            Activity.source.notin_(["polar_dedup", "strava_dedup"]),
        )
    ))

    # Build context for Claude
    targets = {
        "calories":  summary.target_calories if summary else None,
        "carbs_g":   summary.target_carbs_g if summary else None,
        "protein_g": summary.target_protein_g if summary else None,
        "fat_g":     summary.target_fat_g if summary else None,
        "strategy":  summary.carb_strategy if summary else None,
    }

    training_context = {
        "tsb":                summary.tsb if summary else None,
        "total_tss":          summary.total_tss if summary else None,
        "recovery_class":     summary.recovery_classification if summary else None,
        "recommendation":     summary.training_recommendation if summary else None,
        "sessions_today":     [{"sport": a.sport_type, "duration_min": a.duration_seconds // 60,
                                "tss": a.tss} for a in activities],
    }

    dietary_pref  = profile.dietary_preference if profile else "omnivore"
    weight_kg     = profile.weight_kg if profile else 75
    protein_per_kg = profile.protein_target_per_kg if profile else 1.8

    if not targets["calories"]:
        return {
            "error": "No nutrition targets — complete your profile first",
            "meals": [],
        }

    prompt = f"""You are a sports nutritionist for an endurance athlete (runner/cyclist).

Today's nutrition targets:
- Calories: {targets['calories']:.0f} kcal
- Carbohydrates: {targets['carbs_g']:.0f}g
- Protein: {targets['protein_g']:.0f}g  
- Fat: {targets['fat_g']:.0f}g
- Strategy: {targets['strategy']} carb day

Athlete profile:
- Weight: {weight_kg}kg
- Dietary preference: {dietary_pref}
- Protein target: {protein_per_kg}g/kg

Training context:
- Recovery classification: {training_context['recovery_class']}
- TSB (form): {training_context['tsb']}
- Today's recommendation: {training_context['recommendation']}
- Sessions today: {training_context['sessions_today']}

Generate a practical daily meal plan that hits the targets above.
Consider the training context — if there's a hard session, time carbs around it.

Respond ONLY with a JSON object in this exact format, no preamble:
{{
  "day_summary": "One sentence about today's nutrition focus",
  "timing_note": "Key timing advice based on training (pre/post workout, etc)",
  "meals": [
    {{
      "meal_type": "breakfast|lunch|dinner|snack|pre_workout|post_workout",
      "name": "Meal name",
      "description": "Brief description with key ingredients",
      "timing": "When to eat this",
      "calories": 650,
      "carbs_g": 85,
      "protein_g": 35,
      "fat_g": 18,
      "why": "One sentence explaining why this meal fits today's needs"
    }}
  ],
  "hydration_note": "Daily hydration target and timing",
  "supplement_note": "Any relevant supplement timing (optional)"
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
		    "Content-Type": "application/json",
		    "x-api-key": settings.anthropic_api_key,
		    "anthropic-version": "2023-06-01",
		},
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if r.status_code != 200:
                raise HTTPException(502, f"AI API error: {r.status_code}")

            content = r.json()["content"][0]["text"]

            # Strip markdown fences if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            result = json.loads(content)
            return result

    except Exception as e:
        return {
            "error": f"Could not generate recommendations: {str(e)}",
            "meals": [],
        }
