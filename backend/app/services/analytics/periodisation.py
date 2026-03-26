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


# ─── Weekly training templates ────────────────────────────────────────────────

"""
Templates define the STRUCTURE of a training week per phase and race type.
Not a fixed calendar — a pattern the athlete maps onto their own schedule.

Each session:
  type         : run | ride | strength | rest | walk
  label        : short name
  zone         : zone1 | zone2 | tempo | threshold | race_pace | rest
  duration_min : suggested minutes
  purpose      : what physiological adaptation this targets
  notes        : practical cues
  key          : True if this is the session that must not be skipped
"""

SESSION_ZONES = {
    "zone1":      {"label": "Zone 1 — Recovery",   "color": "#94a3b8"},
    "zone2":      {"label": "Zone 2 — Aerobic",     "color": "#60a5fa"},
    "tempo":      {"label": "Zone 3 — Tempo",       "color": "#a78bfa"},
    "threshold":  {"label": "Zone 4 — Threshold",   "color": "#fb923c"},
    "race_pace":  {"label": "Race Pace",             "color": "#e8ff47"},
    "rest":       {"label": "Full Rest",             "color": "#475569"},
}

def _session(type, label, zone, duration, purpose, notes="", key=False):
    return {
        "type":         type,
        "label":        label,
        "zone":         zone,
        "zone_label":   SESSION_ZONES.get(zone, {}).get("label", zone),
        "zone_color":   SESSION_ZONES.get(zone, {}).get("color", "#94a3b8"),
        "duration_min": duration,
        "purpose":      purpose,
        "notes":        notes,
        "key":          key,
    }

def _rest(note=""):
    return _session("rest", "Rest", "rest", 0, "Recovery and adaptation", note)


# ─── Half Marathon templates ──────────────────────────────────────────────────

HALF_MARATHON_TEMPLATES = {
    "base": {
        "focus": "Build aerobic engine. High volume, low intensity. Cycling as cross-training to add load without run injury risk.",
        "intensity_split": "80% easy, 20% moderate",
        "key_session": "Long run",
        "days": [
            _rest("Active recovery — stretch, mobility"),
            _session("run",  "Easy run",           "zone2",     45,  "Aerobic base building", "Conversational pace. HR 68-83% LTHR"),
            _session("ride", "Aerobic ride",        "zone2",     75,  "Cross-training aerobic base", "Builds CTL without run stress"),
            _session("run",  "Easy run",            "zone2",     40,  "Aerobic base", "Same easy effort as Tuesday"),
            _session("ride", "Easy ride or rest",   "zone1",     60,  "Active recovery", "Optional — skip if tired"),
            _session("run",  "Long run",            "zone2",     90,  "Aerobic endurance, fat adaptation", "KEY SESSION — slow and steady, HR under 80% LTHR", key=True),
            _rest("Complete rest or gentle walk"),
        ],
        "weekly_note": "This phase is about volume, not intensity. Resist the urge to push the pace. The aerobic base you build here determines your ceiling in the build phase.",
    },
    "build": {
        "focus": "Introduce quality. Threshold work 1-2×/week. Long run gets longer. Cycling shifts to recovery role.",
        "intensity_split": "75% easy, 25% quality",
        "key_session": "Threshold intervals",
        "days": [
            _rest("Full rest — essential after weekend long run"),
            _session("run",  "Threshold intervals", "threshold", 55,  "Lactate threshold improvement", "4-6×1km at 95-100% LTHR with 90s recovery. KEY SESSION", key=True),
            _session("run",  "Easy recovery run",   "zone2",     40,  "Flush legs from Tuesday", "Very easy. If legs are heavy, drop to 30 min"),
            _session("ride", "Aerobic ride",         "zone2",     75,  "Aerobic load without run stress", "Good day for a longer ride — legs are fresher"),
            _session("run",  "Tempo run",            "tempo",     40,  "Comfortably hard sustained effort", "15 min warm-up, 20 min at 84-94% LTHR, 5 min cool-down"),
            _session("run",  "Long run",             "zone2",    100,  "Endurance — building to 21km", "Last 15-20 min can be at marathon pace. KEY SESSION", key=True),
            _session("ride", "Easy ride or rest",    "zone1",     45,  "Active recovery", "Keep it genuinely easy"),
        ],
        "weekly_note": "Two quality sessions (Tuesday threshold + Friday tempo) are the heart of this week. Everything else exists to support them. Do not do two hard sessions back-to-back.",
    },
    "peak": {
        "focus": "Race-specific. Volume drops slightly, intensity stays high. Introduce half marathon pace work.",
        "intensity_split": "70% easy, 30% quality",
        "key_session": "Race pace run",
        "days": [
            _rest("Full rest"),
            _session("run",  "Threshold intervals", "threshold", 55,  "Maintain lactate threshold fitness", "5×1km at LTHR. Less volume than build phase"),
            _session("run",  "Easy run",            "zone2",     35,  "Recovery", "Short and easy"),
            _session("ride", "Easy ride",            "zone1",     60,  "Active recovery", "No intensity — legs need to be fresh for Friday"),
            _session("run",  "Race pace run",        "race_pace", 50,  "Half marathon pace rehearsal", "10 min warm-up, 30 min at target race pace, 10 min cool-down. KEY SESSION", key=True),
            _session("run",  "Long run",             "zone2",     85,  "Endurance maintenance, confidence", "Similar to build but not longer. Final 20 min at race pace", key=True),
            _rest("Full rest"),
        ],
        "weekly_note": "This is where fitness becomes race fitness. The Friday race pace run is critical — it teaches your body what race day feels like. Long run is slightly shorter than peak build to allow quality on Friday.",
    },
    "taper": {
        "focus": "Freshness. Volume drops 40-50%. Intensity maintained. Trust the process.",
        "intensity_split": "80% easy, 20% sharp",
        "key_session": "Race pace strides",
        "days": [
            _rest("Full rest"),
            _session("run",  "Easy run + strides",  "zone2",     35,  "Maintain feel, freshness building", "30 min easy + 4×20s strides at race pace. Legs should feel good"),
            _rest("Rest or easy walk"),
            _session("run",  "Easy run",            "zone2",     25,  "Keep legs turning over", "Very short. No effort."),
            _session("run",  "Race pace strides",   "race_pace", 30,  "Stay sharp, confirm race pace feels easy", "20 min easy + 4×1 min at race pace. KEY SESSION", key=True),
            _session("run",  "Easy shakeout",       "zone1",     20,  "Stay loose", "Day before race — 15-20 min jog only"),
            {"type": "race", "label": "🏁 Race Day", "zone": "race_pace", "zone_label": "Race Pace", "zone_color": "#e8ff47", "duration_min": 0, "purpose": "Execute your plan", "notes": "Start conservative. First 5km should feel embarrassingly easy.", "key": True},
        ],
        "weekly_note": "The fitness is locked in. You cannot gain fitness this week — you can only lose freshness. Less is more. Every extra easy run you skip this week is a gift to race day you.",
    },
}


# ─── Marathon templates ───────────────────────────────────────────────────────

MARATHON_TEMPLATES = {
    "base": {
        "focus": "Build mileage base. Slow, consistent aerobic running. Cycling supplements without adding run injury risk.",
        "intensity_split": "85% easy, 15% moderate",
        "key_session": "Long run",
        "days": [
            _rest("Full rest — critical for adaptation"),
            _session("run",  "Easy run",          "zone2",     50,  "Aerobic base", "Comfortable conversational pace throughout"),
            _session("ride", "Aerobic ride",       "zone2",     90,  "Additional aerobic stimulus", "Good day for a longer ride"),
            _session("run",  "Easy run",           "zone2",     45,  "Aerobic volume", "Same pace as Tuesday"),
            _session("run",  "Easy run",           "zone2",     40,  "Aerobic base", "Can swap for easy ride if legs tired"),
            _session("run",  "Long run",           "zone2",    110,  "Aerobic endurance, glycogen depletion", "KEY SESSION — build weekly. HR never above 80% LTHR", key=True),
            _rest("Walk or gentle cycling only"),
        ],
        "weekly_note": "Marathon base is about consistent easy running. More is not better — consistent is better. Every run at the right pace contributes. Every run too fast costs recovery.",
    },
    "build": {
        "focus": "Introduce marathon pace. Midweek quality sessions. Long run becomes the week's centrepiece.",
        "intensity_split": "80% easy, 20% quality",
        "key_session": "Marathon pace long run",
        "days": [
            _rest("Full rest"),
            _session("run",  "Threshold intervals", "threshold",  60, "Raise lactate threshold", "5-6×1km at LTHR. KEY QUALITY SESSION", key=True),
            _session("run",  "Easy recovery",       "zone2",      40, "Flush Tuesday effort", "Very easy. HR under 75% LTHR"),
            _session("ride", "Aerobic ride",         "zone2",      90, "Aerobic load, legs rested from run", "Great day for a 2-3hr ride"),
            _session("run",  "Marathon pace run",    "race_pace",  50, "Marathon pace economy", "15 min warm-up, 25 min at MP, 10 min cool-down"),
            _session("run",  "Long run",             "zone2",     130, "Endurance, building to 32km", "Last 30-40 min at marathon pace. KEY SESSION", key=True),
            _session("ride", "Easy ride",            "zone1",      45, "Active recovery", "Spin out the legs gently"),
        ],
        "weekly_note": "Two hard sessions (Tuesday + Friday) with the long run on Saturday. Wednesday ride maintains aerobic load while resting the legs for Friday's marathon pace work.",
    },
    "peak": {
        "focus": "Race specificity. Everything simulates race day demands. Volume holds, intensity peaks.",
        "intensity_split": "75% easy, 25% quality",
        "key_session": "Marathon pace long run",
        "days": [
            _rest("Full rest"),
            _session("run",  "Threshold run",        "threshold",  55, "Maintain fitness peak", "4×2km at LTHR with 2 min recovery"),
            _session("run",  "Easy run",             "zone2",      35, "Recovery", "Genuinely easy"),
            _session("ride", "Easy ride",             "zone1",      60, "Recovery ride", "No intensity — saving legs for Saturday"),
            _session("run",  "Marathon pace run",     "race_pace",  60, "Race specificity, confidence building", "10 min warm-up, 40 min at MP, 10 min cool-down. KEY SESSION", key=True),
            _session("run",  "Long run",              "zone2",     120, "Endurance + race pace finish", "Final 40 min at marathon pace. KEY SESSION", key=True),
            _rest("Full rest"),
        ],
        "weekly_note": "This is the hardest week of the cycle. Friday + Saturday is demanding. If you can nail both, confidence going into taper will be very high.",
    },
    "taper": {
        "focus": "Freshness. Drop volume aggressively. Keep some race pace touches to stay sharp.",
        "intensity_split": "85% easy, 15% sharp",
        "key_session": "Marathon pace strides",
        "days": [
            _rest("Full rest"),
            _session("run",  "Easy run + strides",   "zone2",      40, "Maintain feel", "35 min easy + 4×20s at 10K pace strides. Legs feel good"),
            _rest("Rest or gentle walk"),
            _session("run",  "Easy run",             "zone2",      30, "Keep legs turning over", "Short. No effort whatsoever"),
            _session("run",  "Marathon pace strides", "race_pace",  35, "Stay sharp, confirm pace feels controlled", "25 min easy + 5×1 min at MP with 1 min jog. KEY SESSION", key=True),
            _session("run",  "Easy shakeout",        "zone1",      20, "Stay loose the day before", "15-20 min jog. Nothing more."),
            {"type": "race", "label": "🏁 Race Day", "zone": "race_pace", "zone_label": "Marathon Pace", "zone_color": "#e8ff47", "duration_min": 0, "purpose": "Execute your plan", "notes": "Start 10-15 sec/km slower than target pace for first 10km. The back half is where marathons are won.", "key": True},
        ],
        "weekly_note": "Three weeks of taper. This is week 3 (race week). Your legs will feel flat and heavy mid-taper — that is normal and expected. Do not add extra runs to fix it. Trust the process.",
    },
}


# ─── 10K templates ────────────────────────────────────────────────────────────

TEN_K_TEMPLATES = {
    "base": {
        "focus": "Aerobic foundation. Easy volume with cycling cross-training.",
        "intensity_split": "85% easy, 15% moderate",
        "key_session": "Long run",
        "days": [
            _rest(),
            _session("run",  "Easy run",       "zone2",    40, "Aerobic base"),
            _session("ride", "Aerobic ride",    "zone2",    60, "Cross-training"),
            _session("run",  "Easy run",        "zone2",    35, "Aerobic volume"),
            _rest("Or easy walk"),
            _session("run",  "Long run",        "zone2",    70, "Aerobic endurance", "Build weekly toward 12-14km", key=True),
            _rest(),
        ],
        "weekly_note": "Build the aerobic engine before adding intensity.",
    },
    "build": {
        "focus": "Introduce VO2max work and tempo running.",
        "intensity_split": "75% easy, 25% quality",
        "key_session": "VO2max intervals",
        "days": [
            _rest(),
            _session("run",  "VO2max intervals", "threshold", 45, "VO2max development", "6×800m at 5K effort with 90s recovery. KEY SESSION", key=True),
            _session("run",  "Easy recovery",    "zone2",     35, "Recovery from Tuesday"),
            _session("ride", "Aerobic ride",      "zone2",     60, "Aerobic load"),
            _session("run",  "Tempo run",         "tempo",     35, "Lactate threshold", "20 min at 10K goal pace"),
            _session("run",  "Long run",          "zone2",     65, "Endurance base", "", key=True),
            _rest(),
        ],
        "weekly_note": "Two quality sessions build the speed you need for 10K.",
    },
    "peak": {
        "focus": "Race-specific speed. Short and sharp.",
        "intensity_split": "70% easy, 30% quality",
        "key_session": "10K pace work",
        "days": [
            _rest(),
            _session("run",  "10K pace intervals", "threshold", 40, "Race pace economy", "5×1km at 10K goal pace", key=True),
            _session("run",  "Easy run",           "zone2",     30, "Recovery"),
            _rest("Or easy ride 45 min"),
            _session("run",  "Race pace strides",  "race_pace", 35, "Stay sharp", "25 min easy + 6×20s at 5K effort", key=True),
            _session("run",  "Easy long run",      "zone2",     55, "Confidence", "Nothing heroic — just comfortable"),
            _rest(),
        ],
        "weekly_note": "Volume drops, sharpness maintained. Everything is fast but short.",
    },
    "taper": {
        "focus": "Freshness. 7-day taper — very short.",
        "intensity_split": "85% easy, 15% sharp",
        "key_session": "Race pace strides",
        "days": [
            _rest(),
            _session("run",  "Easy run + strides", "zone2",     30, "Stay sharp", "25 min easy + 4×20s fast"),
            _rest(),
            _session("run",  "Easy run",           "zone1",     20, "Stay loose"),
            _session("run",  "Race pace strides",  "race_pace", 25, "Final sharpener", "15 min easy + 4×1 min at 10K pace", key=True),
            _session("run",  "Easy shakeout",      "zone1",     15, "Loosen up"),
            {"type": "race", "label": "🏁 Race Day", "zone": "race_pace", "zone_label": "10K Pace", "zone_color": "#e8ff47", "duration_min": 0, "purpose": "Race", "notes": "Go out at goal pace. Do not start fast.", "key": True},
        ],
        "weekly_note": "Short taper — 7 days. Keep strides in to stay sharp.",
    },
}


# ─── Template registry ────────────────────────────────────────────────────────

TEMPLATES = {
    "half_marathon": HALF_MARATHON_TEMPLATES,
    "marathon":      MARATHON_TEMPLATES,
    "10k":           TEN_K_TEMPLATES,
    "5k":            TEN_K_TEMPLATES,   # same structure, shorter sessions
    "cycling":       HALF_MARATHON_TEMPLATES,  # similar periodisation
    "other":         HALF_MARATHON_TEMPLATES,
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_weekly_template(
    race_type: str,
    phase: str,
    lthr: int | None = None,
) -> dict:
    """
    Return the weekly training template for a race type + phase combination.
    Adds HR targets to each session if LTHR is available.
    """
    race_templates = TEMPLATES.get(race_type, TEMPLATES["other"])
    template = race_templates.get(phase, race_templates.get("base"))
    if not template:
        return {}

    days_with_hr = []
    for i, session in enumerate(template["days"]):
        s = dict(session)
        s["day"] = DAY_NAMES[i]

        # Attach HR targets if LTHR available
        if lthr and session["zone"] not in ("rest", "race_pace"):
            from app.services.analytics.recommendation import ZONE_RANGES
            lo_pct, hi_pct = ZONE_RANGES.get(session["zone"], (0.68, 0.83))
            s["hr_min"] = round(lthr * lo_pct)
            s["hr_max"] = round(lthr * hi_pct)
        elif lthr and session["zone"] == "race_pace":
            # Race pace HR is approximately 90-97% LTHR for half, 85-92% for marathon
            if race_type == "marathon":
                s["hr_min"] = round(lthr * 0.85)
                s["hr_max"] = round(lthr * 0.92)
            else:
                s["hr_min"] = round(lthr * 0.90)
                s["hr_max"] = round(lthr * 0.97)
        else:
            s["hr_min"] = None
            s["hr_max"] = None

        days_with_hr.append(s)

    # Estimate weekly TSS from session durations + zones
    tss_per_hour = {
        "rest": 0, "zone1": 25, "zone2": 50,
        "tempo": 75, "threshold": 100, "race_pace": 90,
    }
    estimated_tss = sum(
        tss_per_hour.get(s["zone"], 50) * s["duration_min"] / 60
        for s in days_with_hr
    )

    return {
        "race_type":        race_type,
        "phase":            phase,
        "focus":            template["focus"],
        "intensity_split":  template["intensity_split"],
        "key_session":      template["key_session"],
        "weekly_note":      template["weekly_note"],
        "estimated_tss":    round(estimated_tss),
        "days":             days_with_hr,
    }
