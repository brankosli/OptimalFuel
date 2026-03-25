"""
Race Periodisation Engine.

Given a Race and current athlete state, computes:
  - Current training phase (base/build/peak/taper/race/recovery)
  - Weekly TSS targets per phase (prescriptive, overridable)
  - CTL projection to race day
  - Predicted TSB on race day
  - Achievability assessment
  - Post-race recovery period

Phase definitions by race type:
  Marathon     : base >18w, build 10-18w, peak 4-10w, taper <3w (21 days)
  Half marathon: base >12w, build 6-12w,  peak 3-6w,  taper <2w (14 days)
  10K          : base >8w,  build 4-8w,   peak 2-4w,  taper <1.5w (10 days)
  5K           : base >6w,  build 3-6w,   peak 1-3w,  taper <1w (7 days)
  Cycling      : same as half_marathon
  Other        : same as half_marathon

CTL targets by race type and priority:
  Marathon A:      80-95   Half A: 65-75
  Marathon B:      70-85   Half B: 55-65
  10K A:           55-70   5K A:   45-60
"""
from __future__ import annotations
from datetime import date, timedelta
from math import exp

# ─── Race config ──────────────────────────────────────────────────────────────

RACE_CONFIG = {
    "marathon": {
        "taper_days":    21,
        "peak_weeks":    6,
        "build_weeks":   8,
        "target_ctl_A":  87,
        "target_ctl_B":  77,
        "target_ctl_C":  65,
        "tsb_target":    18,   # ideal TSB on race day
        "recovery_days": 21,   # post-race easy period
    },
    "half_marathon": {
        "taper_days":    14,
        "peak_weeks":    4,
        "build_weeks":   6,
        "target_ctl_A":  70,
        "target_ctl_B":  60,
        "target_ctl_C":  50,
        "tsb_target":    14,
        "recovery_days": 10,
    },
    "10k": {
        "taper_days":    10,
        "peak_weeks":    3,
        "build_weeks":   5,
        "target_ctl_A":  62,
        "target_ctl_B":  52,
        "target_ctl_C":  45,
        "tsb_target":    12,
        "recovery_days": 7,
    },
    "5k": {
        "taper_days":    7,
        "peak_weeks":    2,
        "build_weeks":   4,
        "target_ctl_A":  55,
        "target_ctl_B":  48,
        "target_ctl_C":  40,
        "tsb_target":    10,
        "recovery_days": 5,
    },
    "cycling": {
        "taper_days":    14,
        "peak_weeks":    4,
        "build_weeks":   6,
        "target_ctl_A":  75,
        "target_ctl_B":  65,
        "target_ctl_C":  55,
        "tsb_target":    14,
        "recovery_days": 7,
    },
    "other": {
        "taper_days":    14,
        "peak_weeks":    4,
        "build_weeks":   6,
        "target_ctl_A":  65,
        "target_ctl_B":  55,
        "target_ctl_C":  45,
        "tsb_target":    12,
        "recovery_days": 7,
    },
}

PHASE_LABELS = {
    "base":      "Base",
    "build":     "Build",
    "peak":      "Peak",
    "taper":     "Taper",
    "race":      "Race Day",
    "recovery":  "Recovery",
    "off":       "Off Season",
}

PHASE_COLORS = {
    "base":     "#60a5fa",   # blue
    "build":    "#a78bfa",   # purple
    "peak":     "#fb923c",   # orange
    "taper":    "#4ade80",   # green
    "race":     "#e8ff47",   # accent
    "recovery": "#94a3b8",   # gray
    "off":      "#475569",   # dark gray
}

# Nutrition strategy per phase
PHASE_NUTRITION = {
    "base":     "Moderate carbs, higher fat — train fat oxidation and metabolic flexibility",
    "build":    "Increase carbs as intensity rises — fuel quality sessions properly",
    "peak":     "High carbs, especially pre/post threshold sessions — maximise glycogen",
    "taper":    "Slightly reduce calories (less volume) but maintain carbs — glycogen priming",
    "race":     "Race week: carb loading protocol — 8-10g carbs/kg body weight for 3 days pre-race",
    "recovery": "High protein (2.0-2.2g/kg) to repair tissue, moderate carbs, no restriction",
}

# CTL decay constants
CTL_DECAY = 1 - exp(-1 / 42)
ATL_DECAY = 1 - exp(-1 / 7)


# ─── Main engine ──────────────────────────────────────────────────────────────

def analyse_race(
    race_date: date,
    race_type: str,
    priority: str,
    current_ctl: float,
    current_atl: float,
    current_tsb: float,
    avg_weekly_tss: float,         # 4-week average weekly TSS
    today: date | None = None,
    override_base_tss: int | None = None,
    override_build_tss: int | None = None,
    override_peak_tss: int | None = None,
) -> dict:

    today = today or date.today()
    cfg   = RACE_CONFIG.get(race_type, RACE_CONFIG["other"])
    days_out = (race_date - today).days

    if days_out < 0:
        # Race is in the past
        days_since = abs(days_out)
        recovery_end = race_date + timedelta(days=cfg["recovery_days"])
        in_recovery = today <= recovery_end
        return {
            "phase":           "recovery" if in_recovery else "off",
            "phase_label":     PHASE_LABELS["recovery"] if in_recovery else PHASE_LABELS["off"],
            "phase_color":     PHASE_COLORS["recovery"] if in_recovery else PHASE_COLORS["off"],
            "days_out":        days_out,
            "days_since_race": days_since,
            "recovery_end":    recovery_end.isoformat(),
            "completed":       True,
        }

    # ── Determine current phase ───────────────────────────────────────────
    taper_start  = race_date - timedelta(days=cfg["taper_days"])
    peak_start   = taper_start - timedelta(weeks=cfg["peak_weeks"])
    build_start  = peak_start - timedelta(weeks=cfg["build_weeks"])
    weeks_out    = days_out / 7

    if today >= taper_start:
        phase = "taper"
    elif today >= peak_start:
        phase = "peak"
    elif today >= build_start:
        phase = "build"
    else:
        phase = "base"

    # Phase dates
    phase_dates = {
        "base_start":   build_start - timedelta(weeks=12),  # approximate
        "build_start":  build_start,
        "peak_start":   peak_start,
        "taper_start":  taper_start,
        "race_date":    race_date,
    }

    # Weeks into current phase
    phase_start_map = {
        "base":  build_start - timedelta(weeks=12),
        "build": build_start,
        "peak":  peak_start,
        "taper": taper_start,
    }
    weeks_in_phase = (today - phase_start_map[phase]).days / 7

    # ── CTL target ────────────────────────────────────────────────────────
    target_ctl = cfg.get(f"target_ctl_{priority}", cfg["target_ctl_A"])

    # ── Weekly TSS targets per phase ──────────────────────────────────────
    # Start from current avg and ramp toward target CTL
    # CTL ≈ weekly_TSS / 7 (rough, since 42-day EWA)
    # More precisely: stable CTL = weekly_TSS / 7 * (1/CTL_DECAY) but simplified:
    needed_weekly_tss = target_ctl * 7 * CTL_DECAY * (1 + 1/42)

    base_tss  = override_base_tss  or round(max(avg_weekly_tss, needed_weekly_tss * 0.70))
    build_tss = override_build_tss or round(needed_weekly_tss * 0.90)
    peak_tss  = override_peak_tss  or round(needed_weekly_tss * 0.95)
    taper_tss = round(peak_tss * 0.50)

    weekly_targets = {
        "base":  base_tss,
        "build": build_tss,
        "peak":  peak_tss,
        "taper": taper_tss,
    }

    # Current phase target (possibly overridden)
    current_phase_tss = weekly_targets[phase]

    # ── CTL projection to race day ────────────────────────────────────────
    projected_ctl, projected_tsb = _project_to_race(
        current_ctl, current_atl, weekly_targets, phase,
        today, taper_start, peak_start, build_start, race_date,
    )

    # ── Achievability ─────────────────────────────────────────────────────
    ctl_gap       = target_ctl - current_ctl
    max_ramp_week = 5.0   # max safe CTL points/week
    weeks_to_peak = (taper_start - today).days / 7

    if weeks_to_peak <= 0:
        achievable   = current_ctl >= target_ctl * 0.90
        gap_label    = "In taper — fitness locked in"
    elif ctl_gap <= 0:
        achievable   = True
        gap_label    = f"Already at target (CTL {current_ctl:.0f} ≥ {target_ctl})"
    else:
        max_possible = current_ctl + weeks_to_peak * max_ramp_week
        achievable   = max_possible >= target_ctl
        if achievable:
            needed_ramp  = ctl_gap / weeks_to_peak
            gap_label    = f"Need +{needed_ramp:.1f} CTL/week for {weeks_to_peak:.0f} weeks"
        else:
            shortfall    = target_ctl - max_possible
            gap_label    = f"Target may be out of reach — ~{shortfall:.0f} CTL short"

    # ── TSB warning ───────────────────────────────────────────────────────
    tsb_target  = cfg["tsb_target"]
    tsb_warning = None
    if projected_tsb < tsb_target - 8:
        tsb_warning = f"Projected race-day TSB ({projected_tsb:+.0f}) is below ideal ({tsb_target:+.0f}) — consider adding an easy day"
    elif projected_tsb > tsb_target + 12:
        tsb_warning = f"Projected race-day TSB ({projected_tsb:+.0f}) is very high — verify taper is not too aggressive"

    # ── Phase milestones ──────────────────────────────────────────────────
    milestones = _build_milestones(phase_dates, race_type, priority, today)

    # ── Dashboard banner text ─────────────────────────────────────────────
    if days_out == 0:
        banner = "🏁 Race Day!"
    elif days_out <= 3:
        banner = f"🏁 {days_out} days to race — trust the taper"
    elif phase == "taper":
        banner = f"Taper · {days_out} days to race · let it come to you"
    elif phase == "peak":
        banner = f"Peak phase · {days_out} days to race · quality over quantity"
    elif phase == "build":
        banner = f"Build phase · {days_out} days to race · stay consistent"
    else:
        banner = f"Base phase · {days_out} days to race · build the engine"

    return {
        # Core
        "phase":              phase,
        "phase_label":        PHASE_LABELS[phase],
        "phase_color":        PHASE_COLORS[phase],
        "days_out":           days_out,
        "weeks_out":          round(weeks_out, 1),
        "weeks_in_phase":     round(max(0, weeks_in_phase), 1),

        # Phase dates
        "build_start":        phase_dates["build_start"].isoformat(),
        "peak_start":         phase_dates["peak_start"].isoformat(),
        "taper_start":        phase_dates["taper_start"].isoformat(),

        # CTL
        "current_ctl":        round(current_ctl, 1),
        "target_ctl":         target_ctl,
        "projected_ctl_race": round(projected_ctl, 1),
        "achievable":         achievable,
        "gap_label":          gap_label,

        # TSB
        "current_tsb":         round(current_tsb, 1),
        "projected_tsb_race":  round(projected_tsb, 1),
        "tsb_target":          tsb_target,
        "tsb_warning":         tsb_warning,

        # TSS targets
        "weekly_targets":      weekly_targets,
        "current_phase_tss":   current_phase_tss,

        # Context
        "banner":              banner,
        "nutrition_guidance":  PHASE_NUTRITION.get(phase, ""),
        "milestones":          milestones,
        "recovery_days":       cfg["recovery_days"],
    }


def _project_to_race(
    ctl: float, atl: float,
    weekly_targets: dict, current_phase: str,
    today: date, taper_start: date, peak_start: date,
    build_start: date, race_date: date,
) -> tuple[float, float]:
    """
    Simulate CTL/ATL forward day by day using the phase TSS targets.
    Returns (projected_ctl_on_race_day, projected_tsb_on_race_day).
    """
    phase_order = ["base", "build", "peak", "taper"]

    def daily_tss_for_date(d: date) -> float:
        if d >= taper_start: phase = "taper"
        elif d >= peak_start: phase = "peak"
        elif d >= build_start: phase = "build"
        else: phase = "base"
        return weekly_targets[phase] / 7

    sim_ctl = ctl
    sim_atl = atl
    for i in range((race_date - today).days):
        d = today + timedelta(days=i)
        daily = daily_tss_for_date(d)
        sim_ctl = sim_ctl + CTL_DECAY * (daily - sim_ctl)
        sim_atl = sim_atl + ATL_DECAY * (daily - sim_atl)

    return sim_ctl, sim_ctl - sim_atl


def _build_milestones(phase_dates: dict, race_type: str, priority: str, today: date) -> list[dict]:
    """Key training milestones shown on the phase timeline."""
    milestones = []
    race_date  = phase_dates["race_date"]
    taper      = phase_dates["taper_start"]
    peak       = phase_dates["peak_start"]
    build      = phase_dates["build_start"]

    def ms(d, label, note=""):
        days_out = (d - today).days
        return {
            "date":     d.isoformat(),
            "label":    label,
            "note":     note,
            "past":     d < today,
            "days_out": days_out,
        }

    milestones.append(ms(build, "Build begins", "Introduce threshold + quality sessions"))
    milestones.append(ms(peak, "Peak phase", "Volume drops, intensity maintained"))
    milestones.append(ms(taper, "Taper begins", "Trust the process — freshness is building"))

    if race_type == "marathon":
        long_run_peak = taper - timedelta(weeks=3)
        milestones.append(ms(long_run_peak, "Last long run", "Final 30-32km effort before taper"))
    elif race_type == "half_marathon":
        long_run_peak = taper - timedelta(weeks=2)
        milestones.append(ms(long_run_peak, "Last long run", "Final 18-20km effort before taper"))

    milestones.append(ms(race_date, "🏁 Race Day", ""))
    milestones.sort(key=lambda x: x["date"])
    return milestones
