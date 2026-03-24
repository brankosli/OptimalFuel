"""
PMC + Sleep + Load Analytics Engine.

Per-day:
  PMC:     CTL, ATL, TSB
  Load:    ACWR (injury risk), training_monotony, training_strain
  Sleep:   sleep_quality_composite, nocturnal_hr_dip, deep_sleep_deficit, sleep_debt_minutes
  Recovery classification (TSB × Sleep matrix)
  Nutrition targets
"""
import logging
from datetime import date, timedelta
from math import exp, sqrt

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Activity, SleepRecord, DailySummary, UserProfile

logger = logging.getLogger(__name__)

CTL_DAYS  = 42
ATL_DAYS  = 7
CTL_DECAY = 1 - exp(-1 / CTL_DAYS)
ATL_DECAY = 1 - exp(-1 / ATL_DAYS)
SLEEP_TARGET_SECONDS = 8 * 3600


# ─── Nutrition ────────────────────────────────────────────────────────────────

def compute_bmr(weight_kg, height_cm, age, sex):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161

def activity_multiplier(tss):
    if tss < 20:  return 1.2
    if tss < 50:  return 1.4
    if tss < 100: return 1.6
    if tss < 150: return 1.8
    if tss < 200: return 2.0
    return 2.2

def carb_strategy(tss, tsb):
    if tss >= 80:   return "high",     0.55, 0.25, 0.20
    elif tss >= 40: return "moderate", 0.45, 0.30, 0.25
    elif tsb > 10:  return "low",      0.30, 0.35, 0.35
    else:           return "moderate", 0.40, 0.35, 0.25


# ─── Recovery ─────────────────────────────────────────────────────────────────

def recovery_score_simple(nightly_recharge, tsb):
    tsb_norm = min(max((tsb + 30) / 50 * 100, 0), 100)
    score = int(0.6 * nightly_recharge + 0.4 * tsb_norm) if nightly_recharge else int(tsb_norm)
    if score >= 75:   return score, "peak"
    elif score >= 55: return score, "high"
    elif score >= 35: return score, "moderate"
    else:             return score, "low"

def classify_recovery(tsb, sleep_quality):
    sq_high    = sleep_quality is not None and sleep_quality >= 65
    sq_unknown = sleep_quality is None

    if tsb >= 10:
        if sq_high or sq_unknown:
            return "peak",        "Peak readiness — race, time trial, or key workout day"
        else:
            return "fresh_tired", "Fresh but under-recovered sleep — quality session, avoid max efforts"
    elif tsb >= 0:
        if sq_high or sq_unknown:
            return "high",    "Well recovered — proceed with planned session"
        else:
            return "caution", "Good form but poor sleep — reduce intensity by 15-20%"
    elif tsb >= -15:
        if sq_high:
            return "moderate", "Building phase — body adapting, proceed with plan"
        elif sq_unknown:
            return "moderate", "Moderate fatigue — proceed with plan, monitor RPE"
        else:
            return "caution",  "Fatigue + poor sleep — easy session, prioritise sleep tonight"
    else:
        if sq_high:
            return "low",       "High training debt — easy session or rest, recovery nutrition priority"
        else:
            return "overreach", "⚠️ High fatigue + poor sleep — rest day strongly recommended"

def compute_sleep_debt(sleep_by_date, current_date, days=7):
    total = 0
    for i in range(1, days + 1):
        s = sleep_by_date.get(current_date - timedelta(days=i))
        if s and s.total_sleep_seconds:
            total += max(0, SLEEP_TARGET_SECONDS - s.total_sleep_seconds)
    return round(total / 60)


# ─── Load quality ─────────────────────────────────────────────────────────────

def compute_acwr(atl, ctl):
    """ATL/CTL. Safe zone 0.8-1.3 (Gabbett 2016)."""
    if not ctl or ctl < 1:
        return None
    return round(atl / ctl, 3)

def compute_training_monotony(daily_tss, current_date, days=7):
    """
    Foster 1998. Weekly mean / std dev.
    >2.0 = overtraining risk even if total load is OK.
    """
    values = [daily_tss.get(current_date - timedelta(days=i), 0.0) for i in range(days)]
    if not any(v > 0 for v in values):
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = sqrt(variance)
    if std == 0:
        return None
    return round(mean / std, 2)

def compute_training_strain(daily_tss, current_date, days=7):
    """Weekly load × monotony."""
    mono = compute_training_monotony(daily_tss, current_date, days)
    if mono is None:
        return None
    weekly = sum(daily_tss.get(current_date - timedelta(days=i), 0.0) for i in range(days))
    return round(weekly * mono, 1)


# ─── Main recompute ───────────────────────────────────────────────────────────

async def recompute_daily_summaries():
    async with AsyncSessionLocal() as session:

        # Exclude polar_dedup activities from load calculations
        activities = list(await session.scalars(
            select(Activity)
            .where(Activity.source != "polar_dedup")
            .order_by(Activity.activity_date)
        ))
        sleep_records = list(await session.scalars(
            select(SleepRecord).order_by(SleepRecord.sleep_date)
        ))
        sleep_by_date = {s.sleep_date: s for s in sleep_records}
        profile = await session.scalar(select(UserProfile).where(UserProfile.id == 1))

        if not activities and not sleep_records:
            print("PMC: no data found, skipping")
            return

        daily_tss:      dict = {}
        daily_calories: dict = {}
        daily_seconds:  dict = {}

        for act in activities:
            d = act.activity_date
            daily_tss[d]      = daily_tss.get(d, 0.0)      + (act.tss or 0.0)
            daily_calories[d] = daily_calories.get(d, 0.0) + (act.calories or 0.0)
            daily_seconds[d]  = daily_seconds.get(d, 0)    + (act.duration_seconds or 0)

        all_dates_set = set(daily_tss.keys()) | set(sleep_by_date.keys())
        if not all_dates_set:
            return

        min_date  = min(all_dates_set)
        max_date  = date.today()
        all_dates = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]

        ctl = 0.0
        atl = 0.0

        for d in all_dates:
            tss = daily_tss.get(d, 0.0)

            ctl = ctl + CTL_DECAY * (tss - ctl)
            atl = atl + ATL_DECAY * (tss - atl)
            tsb = ctl - atl

            sleep    = sleep_by_date.get(d)
            sq       = sleep.sleep_quality_composite if sleep else None
            hr_dip   = sleep.nocturnal_hr_dip if sleep else None
            deep_d   = sleep.deep_sleep_deficit if sleep else None
            recharge = sleep.nightly_recharge_score if sleep else None

            rec_score, rec_label  = recovery_score_simple(recharge, tsb)
            rec_class, rec_recomm = classify_recovery(tsb, sq)
            sleep_debt            = compute_sleep_debt(sleep_by_date, d)

            acwr     = compute_acwr(atl, ctl)
            monotony = compute_training_monotony(daily_tss, d)
            strain   = compute_training_strain(daily_tss, d)

            target_cal = target_carbs = target_protein = target_fat = None
            strategy = None
            if profile and profile.weight_kg and profile.height_cm and profile.age:
                bmr        = compute_bmr(profile.weight_kg, profile.height_cm,
                                          profile.age, profile.sex or "male")
                target_cal = round(bmr * activity_multiplier(tss))
                strategy, cp, pp, fp = carb_strategy(tss, tsb)
                target_carbs   = round(target_cal * cp / 4)
                target_protein = round(target_cal * pp / 4)
                target_fat     = round(target_cal * fp / 9)
                min_prot = round((profile.protein_target_per_kg or 1.8) * profile.weight_kg)
                if target_protein < min_prot:
                    target_protein = min_prot
                    target_carbs   = max(0, round(target_carbs - (min_prot - target_protein) * 4 / 4))

            existing = await session.scalar(
                select(DailySummary).where(DailySummary.summary_date == d)
            )
            vals = dict(
                ctl=round(ctl, 2), atl=round(atl, 2), tsb=round(tsb, 2),
                total_tss=round(tss, 1),
                total_calories_burned=round(daily_calories.get(d, 0.0)),
                total_activity_seconds=daily_seconds.get(d, 0),
                recovery_score=rec_score,
                readiness_label=rec_label,
                recovery_classification=rec_class,
                training_recommendation=rec_recomm,
                acwr=acwr,
                training_monotony=monotony,
                training_strain=strain,
                sleep_quality_composite=sq,
                nocturnal_hr_dip=hr_dip,
                deep_sleep_deficit=deep_d,
                sleep_debt_minutes=sleep_debt,
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
