"""
Daily Training Recommendation Engine.

Synthesises PMC metrics + sleep analytics into a specific, actionable
workout prescription for the next session.

Outputs:
  - sport           : recommended activity type
  - duration_min    : suggested duration in minutes
  - intensity       : zone1 / zone2 / tempo / threshold / rest
  - hr_min/hr_max   : heart rate targets (if LTHR available)
  - tss_target      : expected TSS for the session
  - headline        : short label (e.g. "Quality Threshold Run")
  - detail          : full paragraph with reasoning
  - warnings        : list of flagged risk factors
  - readiness_score : composite 0-100

HR zones from LTHR (Coggan / Allen):
  Zone 1 Recovery  : < 68% LTHR
  Zone 2 Aerobic   : 68 – 83% LTHR
  Zone 3 Tempo     : 84 – 94% LTHR
  Zone 4 Threshold : 95 – 105% LTHR
  Zone 5 VO2max    : > 105% LTHR
"""
from __future__ import annotations


# ─── Zone helpers ─────────────────────────────────────────────────────────────

ZONE_RANGES = {
    "zone1":     (0.00, 0.68),
    "zone2":     (0.68, 0.83),
    "tempo":     (0.84, 0.94),
    "threshold": (0.95, 1.05),
    "vo2max":    (1.06, 1.20),
}

ZONE_LABELS = {
    "zone1":     "Zone 1 — Recovery",
    "zone2":     "Zone 2 — Aerobic base",
    "tempo":     "Zone 3 — Tempo",
    "threshold": "Zone 4 — Threshold",
    "vo2max":    "Zone 5 — VO2max",
    "rest":      "Full rest",
}


def _hr_range(intensity: str, lthr: int | None) -> tuple[int | None, int | None]:
    if not lthr or intensity == "rest":
        return None, None
    lo_pct, hi_pct = ZONE_RANGES.get(intensity, (0.68, 0.83))
    return round(lthr * lo_pct), round(lthr * hi_pct)


def _tss_estimate(duration_min: int, intensity: str) -> int:
    """Rough TSS estimate by zone."""
    tss_per_hour = {
        "rest": 0, "zone1": 25, "zone2": 50,
        "tempo": 75, "threshold": 100, "vo2max": 120,
    }
    rate = tss_per_hour.get(intensity, 50)
    return round(rate * duration_min / 60)


def _consecutive_poor_sleep(sleep_history: list[float | None], threshold: float = 60.0) -> int:
    """Count consecutive nights of poor sleep (below threshold) going back from yesterday."""
    count = 0
    for sq in reversed(sleep_history):
        if sq is not None and sq < threshold:
            count += 1
        elif sq is not None:
            break
    return count


# ─── Main engine ──────────────────────────────────────────────────────────────

def generate_recommendation(
    tsb: float | None,
    atl: float | None,
    ctl: float | None,
    acwr: float | None,
    sleep_quality: float | None,
    sleep_debt_minutes: int | None,
    nocturnal_hr_dip: float | None,
    deep_sleep_deficit: bool | None,
    training_monotony: float | None,
    recovery_classification: str | None,
    lthr: int | None,
    recent_sports: list[str] | None = None,   # sport types last 7 days
    sleep_quality_history: list[float | None] | None = None,  # last 7 nights
) -> dict:

    tsb   = tsb or 0.0
    atl   = atl or 0.0
    ctl   = ctl or 0.0
    acwr  = acwr
    debt  = sleep_debt_minutes or 0
    mono  = training_monotony
    sq    = sleep_quality
    dip   = nocturnal_hr_dip
    cls   = recovery_classification or "moderate"
    sports = recent_sports or []
    sq_history = sleep_quality_history or []

    warnings: list[str] = []

    # ── Consecutive poor sleep ──────────────────────────────────────────────
    consec_poor = _consecutive_poor_sleep(sq_history, threshold=60.0)
    if consec_poor >= 3:
        warnings.append(f"{consec_poor} consecutive nights of poor sleep — fatigue accumulating")

    # ── ANS stress ─────────────────────────────────────────────────────────
    ans_stressed = dip is not None and dip < 8.0
    if ans_stressed:
        warnings.append(f"Non-dipping HR ({dip:.0f}%) — elevated sympathetic tone, avoid hard efforts")

    # ── Sleep debt ─────────────────────────────────────────────────────────
    if debt > 180:
        warnings.append(f"High sleep debt ({debt // 60}h {debt % 60}m) — recovery priority tonight")
    elif debt > 90:
        warnings.append(f"Moderate sleep debt ({debt} min) — prioritise 8+ hrs tonight")

    # ── ACWR ───────────────────────────────────────────────────────────────
    if acwr is not None:
        if acwr > 1.5:
            warnings.append(f"ACWR {acwr:.2f} — DANGER zone, injury risk very high")
        elif acwr > 1.3:
            warnings.append(f"ACWR {acwr:.2f} — caution zone, reduce load today")

    # ── Deep sleep deficit ─────────────────────────────────────────────────
    if deep_sleep_deficit:
        warnings.append("Deep sleep deficit — physical restoration incomplete")

    # ── Monotony ───────────────────────────────────────────────────────────
    if mono and mono > 2.0:
        warnings.append(f"Training monotony {mono:.1f} — vary session type to reduce overtraining risk")

    # ─────────────────────────────────────────────────────────────────────
    # STEP 1: Determine intensity ceiling
    # Priority order: ACWR > ANS stress > fatigue > sleep > normal
    # ─────────────────────────────────────────────────────────────────────

    if acwr is not None and acwr > 1.5:
        intensity = "rest"
        duration  = 0
        sport     = "rest"

    elif (tsb < -20 and (sq is not None and sq < 55)) or cls == "overreach":
        intensity = "zone1"
        duration  = 25
        sport     = "walk"

    elif ans_stressed or consec_poor >= 3:
        intensity = "zone1"
        duration  = 35
        sport     = _suggest_sport(sports, avoid_repeat=True)

    elif acwr is not None and acwr > 1.3:
        intensity = "zone2"
        duration  = 40
        sport     = _suggest_sport(sports, avoid_repeat=True)

    elif tsb < -20:
        intensity = "zone2"
        duration  = 40
        sport     = _suggest_sport(sports, avoid_repeat=False)

    elif tsb < -10 and (sq is not None and sq < 60):
        intensity = "zone2"
        duration  = 50
        sport     = _suggest_sport(sports, avoid_repeat=False)

    elif tsb < -10:
        intensity = "zone2"
        duration  = 55
        sport     = _suggest_sport(sports, avoid_repeat=False)

    elif tsb < 0:
        if sq is not None and sq >= 65:
            intensity = "tempo"
            duration  = 55
        else:
            intensity = "zone2"
            duration  = 50
        sport = _suggest_sport(sports, avoid_repeat=False)

    elif tsb < 10:
        if sq is not None and sq >= 70:
            intensity = "tempo"
            duration  = 60
        else:
            intensity = "zone2"
            duration  = 55
        sport = _suggest_sport(sports, avoid_repeat=False)

    else:
        # TSB >= 10 — peak/high form
        if sq is not None and sq >= 70 and (dip is None or dip >= 8):
            intensity = "threshold"
            duration  = 55
        elif sq is not None and sq < 60:
            intensity = "zone2"
            duration  = 50
        else:
            intensity = "tempo"
            duration  = 60
        sport = _suggest_sport(sports, avoid_repeat=False)

    # ── Monotony override — suggest variety ────────────────────────────────
    if mono and mono > 2.0 and sport != "rest":
        sport = _suggest_variety(sports)

    # ── Compute HR targets ─────────────────────────────────────────────────
    hr_min, hr_max = _hr_range(intensity, lthr)
    tss_target     = _tss_estimate(duration, intensity)

    # ─────────────────────────────────────────────────────────────────────
    # STEP 2: Build headline + detail text
    # ─────────────────────────────────────────────────────────────────────

    headline, detail = _build_text(
        sport, duration, intensity, hr_min, hr_max, lthr,
        tsb, acwr, sq, debt, dip, cls, warnings, ctl,
    )

    # ─────────────────────────────────────────────────────────────────────
    # STEP 3: Composite readiness score (0-100)
    # ─────────────────────────────────────────────────────────────────────
    readiness = _compute_readiness(tsb, acwr, sq, debt, dip)

    return {
        "sport":          sport,
        "duration_min":   duration,
        "intensity":      intensity,
        "intensity_label": ZONE_LABELS.get(intensity, intensity),
        "hr_min":         hr_min,
        "hr_max":         hr_max,
        "tss_target":     tss_target,
        "headline":       headline,
        "detail":         detail,
        "warnings":       warnings,
        "readiness_score": readiness,
    }


# ─── Sport suggestion ─────────────────────────────────────────────────────────

def _suggest_sport(recent: list[str], avoid_repeat: bool) -> str:
    """Suggest sport — avoids repeating same sport 3 days in a row if avoid_repeat."""
    if not avoid_repeat or not recent:
        last = recent[-1] if recent else "run"
        return last if last in ("run", "ride", "strength", "swim") else "run"

    last3 = recent[-3:] if len(recent) >= 3 else recent
    if len(set(last3)) == 1:
        same = last3[0]
        rotation = {"run": "ride", "ride": "run", "strength": "run", "swim": "run"}
        return rotation.get(same, "run")

    last = recent[-1] if recent else "run"
    return last if last in ("run", "ride", "strength", "swim") else "run"


def _suggest_variety(recent: list[str]) -> str:
    """When monotony is high, explicitly suggest a different sport."""
    last = recent[-1] if recent else "run"
    variety = {"run": "strength", "ride": "run", "strength": "ride", "swim": "run"}
    return variety.get(last, "strength")


# ─── Text generation ──────────────────────────────────────────────────────────

def _build_text(
    sport, duration, intensity, hr_min, hr_max, lthr,
    tsb, acwr, sq, debt, dip, cls, warnings, ctl,
) -> tuple[str, str]:

    sport_labels = {
        "run": "Run", "ride": "Ride", "strength": "Strength session",
        "walk": "Easy walk", "swim": "Swim", "rest": "Rest day",
    }
    sport_label = sport_labels.get(sport, sport.title())

    if intensity == "rest":
        headline = "Rest Day"
        detail = (
            "Full rest is recommended today. "
        )
        if acwr and acwr > 1.5:
            detail += f"Your ACWR is {acwr:.2f} — well above the danger threshold of 1.5. "
            detail += "Adding any load now significantly increases injury probability. "
        detail += "Focus on sleep, hydration and recovery nutrition (high protein, moderate carbs)."
        return headline, detail

    zone_label = ZONE_LABELS.get(intensity, intensity)

    if intensity == "threshold":
        headline = f"Quality {sport_label} — Threshold Intervals"
    elif intensity == "tempo":
        headline = f"Tempo {sport_label}"
    elif intensity == "zone2":
        headline = f"Aerobic {sport_label}"
    else:
        headline = f"Easy {sport_label}"

    parts = []

    # Form context
    if tsb >= 10:
        parts.append(f"Your form is excellent (TSB {tsb:+.0f}) — you're fresh and ready to perform.")
    elif tsb >= 0:
        parts.append(f"Your form is good (TSB {tsb:+.0f}) with manageable fatigue.")
    elif tsb >= -10:
        parts.append(f"You're carrying moderate fatigue (TSB {tsb:.0f}) from recent training.")
    else:
        parts.append(f"Fatigue is elevated (TSB {tsb:.0f}) — your body is still processing recent load.")

    # Sleep context
    if sq is not None:
        if sq >= 75:
            parts.append(f"Sleep recovery was strong (quality {sq:.0f}/100).")
        elif sq >= 60:
            parts.append(f"Sleep was adequate (quality {sq:.0f}/100) — recovery is on track.")
        else:
            parts.append(f"Sleep quality was below par ({sq:.0f}/100) — factor this into your effort.")

    # ANS / HR dip
    if dip is not None:
        if dip >= 10:
            parts.append(f"Nocturnal HR dip was healthy ({dip:.0f}%) — your autonomic nervous system recovered well overnight.")
        elif dip >= 8:
            parts.append(f"Nocturnal HR dip was borderline ({dip:.0f}%) — keep intensity controlled.")
        else:
            parts.append(f"Nocturnal HR dip was low ({dip:.0f}%) — sympathetic nervous system is still active. Cap effort at {zone_label}.")

    # ACWR
    if acwr is not None:
        if 0.8 <= acwr <= 1.3:
            parts.append(f"ACWR is {acwr:.2f} — in the safe zone.")
        elif acwr > 1.3:
            parts.append(f"ACWR is {acwr:.2f} — above the caution threshold. Keep today shorter than planned.")

    # Prescription
    if hr_min and hr_max:
        parts.append(
            f"Target: {duration} min {zone_label} at {hr_min}–{hr_max} bpm. "
            f"Estimated TSS: {_tss_estimate(duration, intensity)}."
        )
    else:
        parts.append(
            f"Target: {duration} min at {zone_label}. "
            f"Estimated TSS: {_tss_estimate(duration, intensity)}. "
            f"Set LTHR in Settings for specific HR targets."
        )

    # Sleep debt note
    if debt > 90:
        parts.append(f"Sleep debt is {debt // 60}h {debt % 60}m over the past 7 days — prioritise an early night tonight.")

    detail = " ".join(parts)
    return headline, detail


# ─── Readiness score ──────────────────────────────────────────────────────────

def _compute_readiness(tsb, acwr, sq, debt, dip) -> int:
    """
    Composite readiness score 0-100.
    Weights reflect relative importance of each signal.
    """
    # TSB component: TSB -30 → 0,  TSB +20 → 100
    tsb_norm = min(max((tsb + 30) / 50 * 100, 0), 100)

    # Sleep quality component
    sq_norm = sq if sq is not None else 55.0

    # ACWR component: 1.0 = 100, 1.5 = 0, 0.5 = 50
    if acwr is None:
        acwr_norm = 70.0
    elif acwr > 1.5:
        acwr_norm = 0.0
    elif acwr > 1.3:
        acwr_norm = max(0, (1.5 - acwr) / 0.2 * 50)
    elif acwr >= 0.8:
        acwr_norm = 100.0
    else:
        acwr_norm = max(0, acwr / 0.8 * 70)

    # Sleep debt component: 0 min = 100, 300+ min = 0
    debt_norm = max(0, 100 - (debt or 0) / 3)

    # HR dip component
    if dip is None:
        dip_norm = 70.0
    elif dip >= 10:
        dip_norm = 100.0
    elif dip >= 8:
        dip_norm = 70.0
    else:
        dip_norm = max(0, dip / 8 * 50)

    score = (
        tsb_norm  * 0.30 +
        sq_norm   * 0.25 +
        acwr_norm * 0.20 +
        debt_norm * 0.15 +
        dip_norm  * 0.10
    )
    return min(100, max(0, round(score)))
