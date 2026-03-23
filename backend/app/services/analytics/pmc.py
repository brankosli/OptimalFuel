"""
Performance Management Chart (PMC) + Sleep Analytics Engine.

Computes per day:
  PMC:
  - CTL  — Chronic Training Load (42-day EWA) → Fitness
  - ATL  — Acute Training Load (7-day EWA)    → Fatigue
  - TSB  — Training Stress Balance (CTL-ATL)  → Form

  Sleep-cross analytics:
  - sleep_quality_composite  — weighted score (deep, REM, continuity, duration)
  - nocturnal_hr_dip         — % HR drop during sleep (non-dipping = stress signal)
  - deep_sleep_deficit       — flag if deep sleep < 15%
  - sleep_debt_minutes       — 7-day rolling debt vs 8hr target

  Recovery classification (TSB × Sleep matrix):
  - 8 classifications with plain-language training recommendation
"""
import logging
from datetime import date, timedelta
from math import exp

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, SleepRecord, DailySummary, UserProfile

logger = logging.getLogger(__name__)

# PMC constants
CTL_DAYS = 42
ATL_DAYS = 7
CTL_DECAY = 1 - exp(-1 / CTL_DAYS)
ATL_DECAY = 1 - exp(-1 / ATL_DAYS)

SLEEP_TARGET_SECONDS = 8 * 3600   # 8hr baseline for debt calculation


# ─── Nutrition helpers ────────────────────────────────────────────────────────

def compute_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def activity_multiplier(tss: float) -> float:
    if tss < 20:  return 1.2
    if tss < 50:  return 1.4
    if tss < 100: return 1.6
    if tss < 150: return 1.8
    if tss < 200: return 2.0
    return 2.2


def carb_strategy(tss: float, tsb: float) -> tuple[str, float, float, float]:
    if tss >= 80:   return "high",     0.55, 0.25, 0.20
    elif tss >= 40: return "moderate", 0.45, 0.30, 0.25
    elif tsb > 10:  return "low",      0.30, 0.35, 0.35
    else:           return "moderate", 0.40, 0.35, 0.25


# ─── Recovery scoring ─────────────────────────────────────────────────────────

def recovery_score_simple(nightly_recharge: float | None, tsb: float) -> tuple[int, str]:
    """TSB-based recovery score, boosted by Nightly Recharge if available."""
    tsb_norm = min(max((tsb + 30) / 50 * 100, 0), 100)
    if nightly_recharge is not None:
        score = int(0.6 * nightly_recharge + 0.4 * tsb_norm)
    else:
        score = int(tsb_norm)
    if score >= 75:   return score, "peak"
    elif score >= 55: return score, "high"
    elif score >= 35: return score, "moderate"
    else:             return score, "low"


def classify_recovery(
    tsb: float,
    sleep_quality: float | None,
) -> tuple[str, str]:
    """
    TSB × Sleep Quality recovery classification matrix.

    Returns: (classification, training_recommendation)

    Classification labels:
    - peak         : Fresh + well-recovered → race/test day
    - high         : Good form, good sleep → quality session
    - fresh_tired  : Good form, poor sleep → reduce intensity
    - moderate     : Slight fatigue, good sleep → proceed with plan
    - caution      : Slight fatigue, poor sleep → easy session
    - low          : High fatigue, good sleep → easy/recovery
    - overreach    : High fatigue + poor sleep → rest day
    """
    sq_high = sleep_quality is not None and sleep_quality >= 65
    sq_low  = sleep_quality is not None and sleep_quality < 65
    sq_unknown = sleep_quality is None

    if tsb >= 10:
        if sq_high or sq_unknown:
            return "peak", "Peak readiness — race, time trial, or key workout day"
        else:
            return "fresh_tired", "Fresh but under-recovered sleep — quality session, avoid new max efforts"
    elif tsb >= 0:
        if sq_high or sq_unknown:
            return "high", "Well recovered — proceed with planned session"
        else:
            return "caution", "Good form but poor sleep — reduce session intensity by 15-20%"
    elif tsb >= -15:
        if sq_high:
            return "moderate", "Building phase — body adapting, proceed with plan"
        elif sq_unknown:
            return "moderate", "Moderate fatigue — proceed with plan, monitor RPE"
        else:
            return "caution", "Fatigue + poor sleep — easy session, prioritise tonight's sleep"
    else:
        if sq_high:
            return "low", "High training debt — easy session or rest, recovery nutrition priority"
        else:
            return "overreach", "⚠️ High fatigue + poor sleep — rest day strongly recommended"


def compute_sleep_debt(
    sleep_by_date: dict,
    current_date: date,
    days: int = 7,
) -> int:
    """
    Rolling sleep debt in minutes over the past N days.
    Debt = sum of max(0, TARGET - actual) for each night.
    """
    total_debt_seconds = 0
    for i in range(1, days + 1):
        d = current_date - timedelta(days=i)
        sleep = sleep_by_date.get(d)
        if sleep and sleep.total_sleep_seconds:
            deficit = SLEEP_TARGET_SECONDS - sleep.total_sleep_seconds
            total_debt_seconds += max(0, deficit)
    return round(total_debt_seconds / 60)


# ─── Main recompute ───────────────────────────────────────────────────────────

async def recompute_daily_summaries():
    async with AsyncSessionLocal() as session:
        activities = list(await session.scalars(
            select(Activity).order_by(Activity.activity_date)
        ))
        sleep_records = list(await session.scalars(
            select(SleepRecord).order_by(SleepRecord.sleep_date)
        ))
        sleep_by_date = {s.sleep_date: s for s in sleep_records}
        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))

        if not activities and not sleep_records:
            print("PMC: no data found, skipping")
            return

        # Build daily TSS map
        daily_tss: dict[date, float] = {}
        daily_calories: dict[date, float] = {}
        daily_seconds: dict[date, int] = {}

        for act in activities:
            d = act.activity_date
            daily_tss[d]     = daily_tss.get(d, 0.0) + (act.tss or 0.0)
            daily_calories[d] = daily_calories.get(d, 0.0) + (act.calories or 0.0)
            daily_seconds[d]  = daily_seconds.get(d, 0) + (act.duration_seconds or 0)

        # Date range: earliest of activity or sleep, to today
        all_dates_set = set(daily_tss.keys()) | set(sleep_by_date.keys())
        if not all_dates_set:
            return

        min_date = min(all_dates_set)
        max_date = date.today()
        all_dates = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]

        ctl = 0.0
        atl = 0.0

        for d in all_dates:
            tss = daily_tss.get(d, 0.0)

            # PMC
            ctl = ctl + CTL_DECAY * (tss - ctl)
            atl = atl + ATL_DECAY * (tss - atl)
            tsb = ctl - atl

            # Sleep data for this day
            sleep = sleep_by_date.get(d)
            sq = sleep.sleep_quality_composite if sleep else None
            hr_dip = sleep.nocturnal_hr_dip if sleep else None
            deep_deficit = sleep.deep_sleep_deficit if sleep else None
            recharge = sleep.nightly_recharge_score if sleep else None

            # Recovery score (simple TSB + recharge)
            rec_score, rec_label = recovery_score_simple(recharge, tsb)

            # Recovery classification (TSB × sleep matrix)
            rec_class, rec_recommendation = classify_recovery(tsb, sq)

            # Sleep debt
            sleep_debt = compute_sleep_debt(sleep_by_date, d)

            # Nutrition
            target_cal = target_carbs = target_protein = target_fat = None
            strategy = None

            if profile and profile.weight_kg and profile.height_cm and profile.age:
                bmr = compute_bmr(profile.weight_kg, profile.height_cm,
                                   profile.age, profile.sex or "male")
                target_cal = round(bmr * activity_multiplier(tss))
                strategy, cp, pp, fp = carb_strategy(tss, tsb)
                target_carbs   = round(target_cal * cp / 4)
                target_protein = round(target_cal * pp / 4)
                target_fat     = round(target_cal * fp / 9)

                min_prot = round((profile.protein_target_per_kg or 1.8) * profile.weight_kg)
                if target_protein < min_prot:
                    deficit_kcal   = (min_prot - target_protein) * 4
                    target_protein = min_prot
                    target_carbs   = max(0, round(target_carbs - deficit_kcal / 4))

            # Upsert
            existing = await session.scalar(
                select(DailySummary).where(DailySummary.summary_date == d)
            )
            vals = dict(
                ctl=round(ctl, 2),
                atl=round(atl, 2),
                tsb=round(tsb, 2),
                total_tss=round(tss, 1),
                total_calories_burned=round(daily_calories.get(d, 0.0)),
                total_activity_seconds=daily_seconds.get(d, 0),
                recovery_score=rec_score,
                readiness_label=rec_label,
                sleep_quality_composite=sq,
                nocturnal_hr_dip=hr_dip,
                deep_sleep_deficit=deep_deficit,
                sleep_debt_minutes=sleep_debt,
                recovery_classification=rec_class,
                training_recommendation=rec_recommendation,
                target_calories=target_cal,
                target_carbs_g=target_carbs,
                target_protein_g=target_protein,
                target_fat_g=target_fat,
                carb_strategy=strategy,
            )

            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
            else:
                session.add(DailySummary(summary_date=d, **vals))

        await session.commit()
        print(f"PMC: recomputed {len(all_dates)} daily summaries")
