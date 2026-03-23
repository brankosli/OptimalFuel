"""
Performance Management Chart (PMC) analytics.

Computes for each day:
  - CTL  — Chronic Training Load  (42-day exp. weighted avg of daily TSS) → "Fitness"
  - ATL  — Acute Training Load    (7-day exp. weighted avg of daily TSS)  → "Fatigue"
  - TSB  — Training Stress Balance (CTL - ATL)                            → "Form"

Then derives:
  - Recovery score (from TSB + Polar Nightly Recharge)
  - Daily caloric and macro targets (carb periodisation)
"""
import logging
from datetime import date, timedelta
from math import exp

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, SleepRecord, DailySummary, UserProfile

logger = logging.getLogger(__name__)

# PMC constants (industry standard)
CTL_DAYS = 42    # ~6 weeks — chronic load time constant
ATL_DAYS = 7     # 1 week — acute load time constant
CTL_DECAY = 1 - exp(-1 / CTL_DAYS)
ATL_DECAY = 1 - exp(-1 / ATL_DAYS)


def compute_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor BMR formula."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def activity_multiplier(tss: float) -> float:
    """
    Map daily TSS to an activity multiplier on top of BMR.
    This is more precise than standard sedentary/active categories.
    """
    if tss < 20:    return 1.2    # Rest / very easy
    if tss < 50:    return 1.4    # Easy
    if tss < 100:   return 1.6    # Moderate
    if tss < 150:   return 1.8    # Hard
    if tss < 200:   return 2.0    # Very hard
    return 2.2                    # Extreme (big day)


def carb_strategy(tss: float, tsb: float) -> tuple[str, float, float, float]:
    """
    Determine carb periodisation strategy based on training stress and form.

    Returns: (strategy_label, carb_pct, protein_pct, fat_pct)

    Rules:
    - High TSS day (hard session) → High carb
    - Low TSS + positive TSB (fresh, recovery) → Low carb / fat adaptation
    - Low TSS + negative TSB (tired, rest day) → Moderate, recovery focus
    """
    if tss >= 80:
        # Hard training day — maximise glycogen
        return "high", 0.55, 0.25, 0.20
    elif tss >= 40:
        # Moderate day
        return "moderate", 0.45, 0.30, 0.25
    elif tsb > 10:
        # Easy/rest + good form → fat adaptation window
        return "low", 0.30, 0.35, 0.35
    else:
        # Easy/rest + fatigued → moderate recovery focus
        return "moderate", 0.40, 0.35, 0.25


def recovery_score(nightly_recharge: float | None, tsb: float) -> tuple[int, str]:
    """
    Combine Polar Nightly Recharge (0-100) with TSB to get a composite recovery score.

    If no Nightly Recharge data, fall back to TSB-only heuristic.
    """
    # TSB-based component (TSB typically ranges -30 to +20)
    tsb_norm = min(max((tsb + 30) / 50 * 100, 0), 100)

    if nightly_recharge is not None:
        score = int(0.6 * nightly_recharge + 0.4 * tsb_norm)
    else:
        score = int(tsb_norm)

    if score >= 75:   label = "peak"
    elif score >= 55: label = "high"
    elif score >= 35: label = "moderate"
    else:             label = "low"

    return score, label


async def recompute_daily_summaries():
    """
    Recompute all daily summaries from scratch.
    Called after each sync. Fast enough for personal-scale data.
    """
    async with AsyncSessionLocal() as session:
        # Load all activities with TSS
        activities = await session.scalars(
            select(Activity).order_by(Activity.activity_date)
        )
        activities = list(activities)

        # Load all sleep records
        sleep_records = await session.scalars(
            select(SleepRecord).order_by(SleepRecord.sleep_date)
        )
        sleep_by_date = {s.sleep_date: s for s in sleep_records}

        # Load user profile
        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))

        if not activities:
            logger.info("PMC: no activities found, skipping")
            return

        # Build daily TSS map
        daily_tss: dict[date, float] = {}
        daily_calories: dict[date, float] = {}
        daily_seconds: dict[date, int] = {}

        for act in activities:
            d = act.activity_date
            daily_tss[d] = daily_tss.get(d, 0.0) + (act.tss or 0.0)
            daily_calories[d] = daily_calories.get(d, 0.0) + (act.calories or 0.0)
            daily_seconds[d] = daily_seconds.get(d, 0) + (act.duration_seconds or 0)

        # Determine date range
        min_date = min(daily_tss.keys())
        max_date = date.today()
        all_dates = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]

        # Iterate and compute PMC values using exponential weighted averages
        ctl = 0.0
        atl = 0.0

        for d in all_dates:
            tss = daily_tss.get(d, 0.0)

            # EWA update
            ctl = ctl + CTL_DECAY * (tss - ctl)
            atl = atl + ATL_DECAY * (tss - atl)
            tsb = ctl - atl

            # Recovery
            sleep = sleep_by_date.get(d)
            recharge = sleep.nightly_recharge_score if sleep else None
            rec_score, rec_label = recovery_score(recharge, tsb)

            # Nutrition targets
            target_cal = None
            target_carbs = target_protein = target_fat = None
            strategy = None

            if profile and profile.weight_kg and profile.height_cm and profile.age:
                bmr = compute_bmr(
                    profile.weight_kg, profile.height_cm,
                    profile.age, profile.sex or "male"
                )
                multiplier = activity_multiplier(tss)
                target_cal = round(bmr * multiplier)

                strategy, carb_pct, protein_pct, fat_pct = carb_strategy(tss, tsb)

                # 1g carb = 4 kcal, 1g protein = 4 kcal, 1g fat = 9 kcal
                target_carbs = round(target_cal * carb_pct / 4)
                target_protein = round(target_cal * protein_pct / 4)
                target_fat = round(target_cal * fat_pct / 9)

                # Protein minimum: profile target per kg body weight
                min_protein = round((profile.protein_target_per_kg or 1.8) * profile.weight_kg)
                if target_protein < min_protein:
                    # Redistribute from carbs to meet protein minimum
                    deficit_kcal = (min_protein - target_protein) * 4
                    target_protein = min_protein
                    target_carbs = max(0, round(target_carbs - deficit_kcal / 4))

            # Upsert summary
            existing = await session.scalar(
                select(DailySummary).where(DailySummary.summary_date == d)
            )
            if existing:
                existing.ctl = round(ctl, 2)
                existing.atl = round(atl, 2)
                existing.tsb = round(tsb, 2)
                existing.total_tss = round(daily_tss.get(d, 0.0), 1)
                existing.total_calories_burned = round(daily_calories.get(d, 0.0))
                existing.total_activity_seconds = daily_seconds.get(d, 0)
                existing.recovery_score = rec_score
                existing.readiness_label = rec_label
                existing.target_calories = target_cal
                existing.target_carbs_g = target_carbs
                existing.target_protein_g = target_protein
                existing.target_fat_g = target_fat
                existing.carb_strategy = strategy
            else:
                session.add(DailySummary(
                    summary_date=d,
                    ctl=round(ctl, 2),
                    atl=round(atl, 2),
                    tsb=round(tsb, 2),
                    total_tss=round(daily_tss.get(d, 0.0), 1),
                    total_calories_burned=round(daily_calories.get(d, 0.0)),
                    total_activity_seconds=daily_seconds.get(d, 0),
                    recovery_score=rec_score,
                    readiness_label=rec_label,
                    target_calories=target_cal,
                    target_carbs_g=target_carbs,
                    target_protein_g=target_protein,
                    target_fat_g=target_fat,
                    carb_strategy=strategy,
                ))

        await session.commit()
        logger.info(f"PMC: recomputed {len(all_dates)} daily summaries")
