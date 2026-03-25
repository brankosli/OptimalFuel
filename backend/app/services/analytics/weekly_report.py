"""
Weekly Training Report Engine.

Generates a structured plain-language report for any given ISO week.
Covers: load, fitness trend, ACWR risk, sleep, and next-week guidance.
"""
from __future__ import annotations
from datetime import date, timedelta
from math import sqrt


def _avg(values: list) -> float | None:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None

def _pct_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old == 0:
        return None
    return round((new - old) / abs(old) * 100, 1)

def _trend_arrow(change: float | None) -> str:
    if change is None: return "→"
    if change > 5:  return "↑"
    if change < -5: return "↓"
    return "→"


def generate_weekly_report(
    week_summaries: list[dict],   # 7 DailySummary dicts for the week
    prev_summaries: list[dict],   # 7 DailySummary dicts for previous week
    week_activities: list[dict],  # Activity rows for the week
    week_sleep: list[dict],       # SleepRecord rows for the week
    week_start: date,
    week_end: date,
    lthr: int | None = None,
    ftp: float | None = None,
) -> dict:

    # ── Load metrics ──────────────────────────────────────────────────────
    weekly_tss   = sum(s.get("total_tss") or 0 for s in week_summaries)
    prev_tss     = sum(s.get("total_tss") or 0 for s in prev_summaries)
    tss_change   = _pct_change(prev_tss, weekly_tss)

    total_hours  = sum((a.get("duration_seconds") or 0) for a in week_activities) / 3600
    num_sessions = len(week_activities)

    # CTL start vs end of week
    ctl_start = week_summaries[0].get("ctl") if week_summaries else None
    ctl_end   = week_summaries[-1].get("ctl") if week_summaries else None
    ctl_gain  = round(ctl_end - ctl_start, 1) if ctl_start and ctl_end else None

    atl_end   = week_summaries[-1].get("atl") if week_summaries else None
    tsb_end   = week_summaries[-1].get("tsb") if week_summaries else None
    acwr_vals = [s.get("acwr") for s in week_summaries if s.get("acwr")]
    acwr_max  = max(acwr_vals) if acwr_vals else None
    acwr_avg  = _avg(acwr_vals)

    # Monotony
    mono_vals = [s.get("training_monotony") for s in week_summaries if s.get("training_monotony")]
    mono_avg  = _avg(mono_vals)

    # Daily TSS values for std dev
    daily_tss_vals = [s.get("total_tss") or 0 for s in week_summaries]
    tss_mean = sum(daily_tss_vals) / 7
    tss_std  = sqrt(sum((v - tss_mean) ** 2 for v in daily_tss_vals) / 7)

    # ── Sleep metrics ─────────────────────────────────────────────────────
    sleep_scores   = [s.get("sleep_quality_composite") for s in week_sleep]
    avg_sleep_q    = _avg(sleep_scores)
    deficit_nights = sum(1 for s in week_sleep if s.get("deep_sleep_deficit"))
    avg_hours      = _avg([(s.get("total_sleep_seconds") or 0) / 3600 for s in week_sleep])
    avg_hr_dip     = _avg([s.get("nocturnal_hr_dip") for s in week_sleep])

    # Sleep debt at end of week
    sleep_debt = week_summaries[-1].get("sleep_debt_minutes") if week_summaries else None

    # ── Sport breakdown ───────────────────────────────────────────────────
    sport_counts: dict[str, int] = {}
    sport_tss: dict[str, float] = {}
    for a in week_activities:
        sp = a.get("sport_type", "other")
        sport_counts[sp] = sport_counts.get(sp, 0) + 1
        sport_tss[sp] = sport_tss.get(sp, 0) + (a.get("tss") or 0)

    # ── ACWR assessment ───────────────────────────────────────────────────
    if acwr_max is None:
        acwr_status = "unknown"
    elif acwr_max > 1.5:
        acwr_status = "danger"
    elif acwr_max > 1.3:
        acwr_status = "caution"
    elif acwr_avg and acwr_avg < 0.8:
        acwr_status = "low"
    else:
        acwr_status = "safe"

    # ── Next week guidance ────────────────────────────────────────────────
    next_week_guidance, next_tss_target = _next_week_guidance(
        weekly_tss, prev_tss, acwr_max, acwr_avg,
        avg_sleep_q, tsb_end, ctl_end, mono_avg,
    )

    # ── Narrative sections ────────────────────────────────────────────────
    load_narrative   = _load_narrative(weekly_tss, prev_tss, tss_change, num_sessions,
                                        total_hours, ctl_gain, ctl_end, tsb_end)
    acwr_narrative   = _acwr_narrative(acwr_max, acwr_avg, acwr_status)
    sleep_narrative  = _sleep_narrative(avg_sleep_q, avg_hours, deficit_nights,
                                         avg_hr_dip, sleep_debt)
    recovery_narrative = _recovery_narrative(tsb_end, avg_sleep_q, acwr_status)

    # ── Highlights & alerts ───────────────────────────────────────────────
    highlights = _build_highlights(
        tss_change, ctl_gain, acwr_max, avg_sleep_q,
        deficit_nights, sleep_debt, mono_avg, num_sessions,
    )

    return {
        "week_start":      week_start.isoformat(),
        "week_end":        week_end.isoformat(),
        "week_label":      f"Week of {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}",

        # ── Load ──────────────────────────────────────────────────────────
        "weekly_tss":      round(weekly_tss, 1),
        "prev_tss":        round(prev_tss, 1),
        "tss_change_pct":  tss_change,
        "tss_arrow":       _trend_arrow(tss_change),
        "total_hours":     round(total_hours, 1),
        "num_sessions":    num_sessions,
        "sport_breakdown": sport_counts,
        "sport_tss":       {k: round(v, 1) for k, v in sport_tss.items()},

        # ── Fitness ───────────────────────────────────────────────────────
        "ctl_start":       round(ctl_start, 1) if ctl_start else None,
        "ctl_end":         round(ctl_end, 1) if ctl_end else None,
        "ctl_gain":        ctl_gain,
        "atl_end":         round(atl_end, 1) if atl_end else None,
        "tsb_end":         round(tsb_end, 1) if tsb_end else None,

        # ── Risk ──────────────────────────────────────────────────────────
        "acwr_max":        round(acwr_max, 2) if acwr_max else None,
        "acwr_avg":        round(acwr_avg, 2) if acwr_avg else None,
        "acwr_status":     acwr_status,
        "training_monotony": round(mono_avg, 2) if mono_avg else None,

        # ── Sleep ─────────────────────────────────────────────────────────
        "avg_sleep_quality":  round(avg_sleep_q, 1) if avg_sleep_q else None,
        "avg_sleep_hours":    round(avg_hours, 1) if avg_hours else None,
        "deficit_nights":     deficit_nights,
        "avg_hr_dip":         round(avg_hr_dip, 1) if avg_hr_dip else None,
        "sleep_debt_minutes": sleep_debt,

        # ── Narratives ────────────────────────────────────────────────────
        "load_narrative":      load_narrative,
        "acwr_narrative":      acwr_narrative,
        "sleep_narrative":     sleep_narrative,
        "recovery_narrative":  recovery_narrative,

        # ── Next week ─────────────────────────────────────────────────────
        "next_week_guidance":  next_week_guidance,
        "next_tss_target":     next_tss_target,

        # ── Summary ───────────────────────────────────────────────────────
        "highlights":          highlights,
    }


# ─── Narrative builders ───────────────────────────────────────────────────────

def _load_narrative(tss, prev_tss, change, sessions, hours, ctl_gain, ctl_end, tsb) -> str:
    parts = []

    if tss > 0:
        parts.append(f"You completed {sessions} session{'s' if sessions != 1 else ''} "
                     f"totalling {hours:.1f} hours and {tss:.0f} TSS.")
    else:
        return "No training data recorded for this week."

    if change is not None:
        if change > 15:
            parts.append(f"Load jumped {change:.0f}% from the previous week — a significant spike.")
        elif change > 5:
            parts.append(f"Load increased {change:.0f}% from last week — solid progression.")
        elif change < -15:
            parts.append(f"Load dropped {abs(change):.0f}% from last week — a meaningful recovery week.")
        elif change < -5:
            parts.append(f"Load eased back {abs(change):.0f}% from last week.")
        else:
            parts.append("Load was consistent with last week.")

    if ctl_gain is not None and ctl_end is not None:
        if ctl_gain > 0:
            parts.append(f"Fitness (CTL) grew by {ctl_gain} points to {ctl_end:.0f} — your aerobic base is building.")
        elif ctl_gain < -1:
            parts.append(f"Fitness (CTL) dipped {abs(ctl_gain)} points to {ctl_end:.0f} — expected if this was a recovery week.")
        else:
            parts.append(f"Fitness (CTL) held steady at {ctl_end:.0f}.")

    if tsb is not None:
        if tsb > 10:
            parts.append(f"Form is positive (TSB {tsb:+.0f}) — you're carrying freshness into next week.")
        elif tsb > -5:
            parts.append(f"Form is neutral (TSB {tsb:+.0f}) — well-balanced week.")
        elif tsb > -15:
            parts.append(f"Form is slightly negative (TSB {tsb:.0f}) — normal for a building week.")
        else:
            parts.append(f"Form is significantly negative (TSB {tsb:.0f}) — rest is warranted.")

    return " ".join(parts)


def _acwr_narrative(acwr_max, acwr_avg, status) -> str:
    if status == "unknown":
        return "ACWR could not be calculated — ensure TSS data is available."
    if status == "danger":
        return (f"⚠️ ACWR peaked at {acwr_max:.2f} this week — well above the 1.5 danger threshold. "
                f"This represents a significant spike in load relative to your chronic fitness. "
                f"Injury risk is elevated. Next week must include mandatory easy days.")
    if status == "caution":
        return (f"ACWR peaked at {acwr_max:.2f}, briefly entering the caution zone (above 1.3). "
                f"Average was {acwr_avg:.2f}. Monitor fatigue closely and avoid back-to-back hard sessions next week.")
    if status == "low":
        return (f"ACWR averaged {acwr_avg:.2f} — below the 0.8 threshold, indicating a detraining risk. "
                f"Gradually increasing load next week is recommended to maintain fitness.")
    return (f"ACWR stayed in the safe zone (avg {acwr_avg:.2f}, max {acwr_max:.2f}). "
            f"Load was well-managed relative to your chronic fitness level.")


def _sleep_narrative(avg_q, avg_hours, deficit_nights, avg_dip, debt) -> str:
    if avg_q is None:
        return "No sleep data available for this week."

    parts = []

    if avg_q >= 75:
        parts.append(f"Sleep quality was excellent this week (avg {avg_q:.0f}/100).")
    elif avg_q >= 60:
        parts.append(f"Sleep quality was adequate (avg {avg_q:.0f}/100).")
    else:
        parts.append(f"Sleep quality was below par this week (avg {avg_q:.0f}/100).")

    if avg_hours:
        if avg_hours >= 7.5:
            parts.append(f"Average duration was {avg_hours:.1f} hours — well within the optimal range.")
        elif avg_hours >= 7:
            parts.append(f"Average duration was {avg_hours:.1f} hours — adequate.")
        else:
            parts.append(f"Average duration was only {avg_hours:.1f} hours — below the recommended 7-9 hours.")

    if deficit_nights > 0:
        parts.append(f"{deficit_nights} night{'s' if deficit_nights > 1 else ''} showed deep sleep deficit, "
                     f"meaning physical restoration was incomplete on those nights.")

    if avg_dip is not None:
        if avg_dip >= 10:
            parts.append(f"Nocturnal HR dip averaged {avg_dip:.0f}% — healthy autonomic recovery.")
        elif avg_dip >= 8:
            parts.append(f"Nocturnal HR dip averaged {avg_dip:.0f}% — borderline, suggesting mild stress.")
        else:
            parts.append(f"Nocturnal HR dip averaged {avg_dip:.0f}% — non-dipping pattern indicates elevated sympathetic tone.")

    if debt and debt > 120:
        parts.append(f"You entered next week with {debt // 60}h {debt % 60}m of accumulated sleep debt.")

    return " ".join(parts)


def _recovery_narrative(tsb, sleep_q, acwr_status) -> str:
    if tsb is None:
        return "Insufficient data for recovery assessment."

    lines = []
    if tsb > 10 and (sleep_q is None or sleep_q >= 60) and acwr_status == "safe":
        lines.append("Overall recovery is strong heading into next week.")
        lines.append("Your body is primed for quality training — this is a good time to schedule a key session.")
    elif tsb > 0 and acwr_status in ("safe", "unknown"):
        lines.append("Recovery is on track. Moderate fatigue is manageable and normal for a training block.")
    elif tsb < -15 or acwr_status == "danger":
        lines.append("Recovery is compromised. The combination of accumulated fatigue and load spike warrants a mandatory easy week.")
    else:
        lines.append("Recovery is moderate. Listen to your body and don't force intensity if fatigue persists.")

    return " ".join(lines)


def _next_week_guidance(tss, prev_tss, acwr_max, acwr_avg, sleep_q, tsb, ctl, mono) -> tuple[str, int | None]:
    """Returns (guidance_text, recommended_tss_target)."""

    if acwr_max and acwr_max > 1.5:
        target = round(tss * 0.7)
        return (f"Mandatory reduction week. Cap TSS at ~{target} (30% reduction). "
                f"No sessions above Zone 2. Focus on sleep and recovery nutrition.", target)

    if acwr_max and acwr_max > 1.3:
        target = round(tss * 0.85)
        return (f"Ease back slightly — cap TSS at ~{target}. "
                f"Keep ACWR below 1.3 by spacing hard sessions with easy days.", target)

    if tsb is not None and tsb < -20:
        target = round(tss * 0.8)
        return (f"Fatigue is high. Reduce to ~{target} TSS and include at least 2 full rest days.", target)

    if sleep_q is not None and sleep_q < 55:
        target = round(tss * 0.9)
        return (f"Sleep quality was poor this week. Maintain load at ~{target} TSS "
                f"but prioritise sleep hygiene — it limits your ability to adapt to training.", target)

    if mono and mono > 2.0:
        target = round(tss * 1.0)
        return (f"Vary your training — high monotony ({mono:.1f}) increases overtraining risk. "
                f"Include different sport types and session lengths. Keep total TSS around {target}.", target)

    # Normal progression — standard 5-8% ramp
    target = round(tss * 1.06)
    return (f"Good week. A ~5% load increase is appropriate — target {target} TSS next week. "
            f"Continue mixing intensities and monitor how ACWR responds.", target)


def _build_highlights(tss_change, ctl_gain, acwr_max, sleep_q,
                       deficit_nights, sleep_debt, mono, sessions) -> list[dict]:
    """Key stat badges for the summary header."""
    items = []

    if tss_change is not None:
        items.append({
            "label": "Load vs last week",
            "value": f"{'+' if tss_change > 0 else ''}{tss_change:.0f}%",
            "status": "warning" if abs(tss_change) > 20 else "ok",
        })

    if ctl_gain is not None:
        items.append({
            "label": "Fitness change",
            "value": f"{'+' if ctl_gain > 0 else ''}{ctl_gain} CTL",
            "status": "good" if ctl_gain > 0 else "neutral",
        })

    if acwr_max is not None:
        items.append({
            "label": "Peak ACWR",
            "value": f"{acwr_max:.2f}",
            "status": "danger" if acwr_max > 1.5 else "warning" if acwr_max > 1.3 else "good",
        })

    if sleep_q is not None:
        items.append({
            "label": "Avg sleep quality",
            "value": f"{sleep_q:.0f}/100",
            "status": "good" if sleep_q >= 70 else "warning" if sleep_q >= 55 else "bad",
        })

    if deficit_nights > 0:
        items.append({
            "label": "Deep sleep deficits",
            "value": f"{deficit_nights} nights",
            "status": "warning" if deficit_nights <= 2 else "bad",
        })

    if sessions > 0:
        items.append({
            "label": "Sessions",
            "value": str(sessions),
            "status": "ok",
        })

    return items
