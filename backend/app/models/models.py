"""
SQLAlchemy ORM models.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, Date, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


# ─── OAuth Tokens ─────────────────────────────────────────────────────────────

class PolarToken(Base):
    __tablename__ = "polar_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    polar_user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StravaToken(Base):
    __tablename__ = "strava_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    athlete_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Activities ───────────────────────────────────────────────────────────────

class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    calories: Mapped[Optional[float]] = mapped_column(Float)
    distance_meters: Mapped[Optional[float]] = mapped_column(Float)
    elevation_gain_meters: Mapped[Optional[float]] = mapped_column(Float)
    avg_heart_rate: Mapped[Optional[int]] = mapped_column(Integer)
    max_heart_rate: Mapped[Optional[int]] = mapped_column(Integer)
    training_load: Mapped[Optional[float]] = mapped_column(Float)
    suffer_score: Mapped[Optional[int]] = mapped_column(Integer)
    tss: Mapped[Optional[float]] = mapped_column(Float)
    avg_power_watts: Mapped[Optional[float]] = mapped_column(Float)
    normalized_power_watts: Mapped[Optional[float]] = mapped_column(Float)
    ftp_watts: Mapped[Optional[float]] = mapped_column(Float)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Sleep ────────────────────────────────────────────────────────────────────

class SleepRecord(Base):
    __tablename__ = "sleep_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="polar")
    source_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    sleep_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    bedtime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    wake_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    light_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    deep_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    rem_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    unrecognized_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    deep_pct: Mapped[Optional[float]] = mapped_column(Float)
    rem_pct: Mapped[Optional[float]] = mapped_column(Float)
    light_pct: Mapped[Optional[float]] = mapped_column(Float)
    sleep_score: Mapped[Optional[int]] = mapped_column(Integer)
    sleep_charge: Mapped[Optional[float]] = mapped_column(Float)
    nightly_recharge_score: Mapped[Optional[int]] = mapped_column(Integer)
    ans_charge: Mapped[Optional[float]] = mapped_column(Float)
    sleep_cycles: Mapped[Optional[int]] = mapped_column(Integer)
    continuity: Mapped[Optional[float]] = mapped_column(Float)
    continuity_class: Mapped[Optional[int]] = mapped_column(Integer)
    total_interruption_duration: Mapped[Optional[int]] = mapped_column(Integer)
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer)
    nocturnal_hr_min: Mapped[Optional[int]] = mapped_column(Integer)
    nocturnal_hr_dip: Mapped[Optional[float]] = mapped_column(Float)
    breathing_rate: Mapped[Optional[float]] = mapped_column(Float)
    hrv_avg_ms: Mapped[Optional[float]] = mapped_column(Float)
    hrv_rmssd: Mapped[Optional[float]] = mapped_column(Float)
    sleep_quality_composite: Mapped[Optional[float]] = mapped_column(Float)
    deep_sleep_deficit: Mapped[Optional[bool]] = mapped_column(Boolean)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Daily Summary ────────────────────────────────────────────────────────────

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    # PMC
    ctl: Mapped[Optional[float]] = mapped_column(Float)
    atl: Mapped[Optional[float]] = mapped_column(Float)
    tsb: Mapped[Optional[float]] = mapped_column(Float)

    # Training totals
    total_tss: Mapped[Optional[float]] = mapped_column(Float)
    total_calories_burned: Mapped[Optional[float]] = mapped_column(Float)
    total_activity_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Recovery
    recovery_score: Mapped[Optional[int]] = mapped_column(Integer)
    readiness_label: Mapped[Optional[str]] = mapped_column(String(20))
    recovery_classification: Mapped[Optional[str]] = mapped_column(String(30))
    training_recommendation: Mapped[Optional[str]] = mapped_column(String(255))

    # Load quality metrics (NEW)
    acwr: Mapped[Optional[float]] = mapped_column(Float)              # ATL/CTL — injury risk
    training_monotony: Mapped[Optional[float]] = mapped_column(Float) # Foster 1998
    training_strain: Mapped[Optional[float]] = mapped_column(Float)   # weekly load × monotony

    # Sleep analytics
    sleep_quality_composite: Mapped[Optional[float]] = mapped_column(Float)
    nocturnal_hr_dip: Mapped[Optional[float]] = mapped_column(Float)
    deep_sleep_deficit: Mapped[Optional[bool]] = mapped_column(Boolean)
    sleep_debt_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    # Nutrition targets
    target_calories: Mapped[Optional[float]] = mapped_column(Float)
    target_carbs_g: Mapped[Optional[float]] = mapped_column(Float)
    target_protein_g: Mapped[Optional[float]] = mapped_column(Float)
    target_fat_g: Mapped[Optional[float]] = mapped_column(Float)
    carb_strategy: Mapped[Optional[str]] = mapped_column(String(20))

    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Nutrition Log ────────────────────────────────────────────────────────────

class MealLog(Base):
    __tablename__ = "meal_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    calories: Mapped[Optional[float]] = mapped_column(Float)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float)
    protein_g: Mapped[Optional[float]] = mapped_column(Float)
    fat_g: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── User Profile ─────────────────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    height_cm: Mapped[Optional[float]] = mapped_column(Float)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    sex: Mapped[Optional[str]] = mapped_column(String(10))
    ftp_watts: Mapped[Optional[float]] = mapped_column(Float)
    lthr_bpm: Mapped[Optional[int]] = mapped_column(Integer)
    vo2max: Mapped[Optional[float]] = mapped_column(Float)
    dietary_preference: Mapped[Optional[str]] = mapped_column(String(50))
    protein_target_per_kg: Mapped[float] = mapped_column(Float, default=1.8)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Race Calendar ────────────────────────────────────────────────────────────

class Race(Base):
    """
    User-managed race calendar entry.
    Phases, CTL targets and TSS targets are computed on the fly
    from race_date + race_type — no extra tables needed.
    """
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    race_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    race_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # marathon | half_marathon | 10k | 5k | cycling | other

    priority: Mapped[str] = mapped_column(String(5), nullable=False, default="A")
    # A | B | C | test

    target_finish_time: Mapped[Optional[str]] = mapped_column(String(10))  # "1:45:00"
    actual_finish_time: Mapped[Optional[str]] = mapped_column(String(10))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Override weekly TSS targets per phase (null = use computed defaults)
    override_base_tss: Mapped[Optional[int]] = mapped_column(Integer)
    override_build_tss: Mapped[Optional[int]] = mapped_column(Integer)
    override_peak_tss: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                   onupdate=datetime.utcnow)
