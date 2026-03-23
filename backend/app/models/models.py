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
    """
    Nightly sleep data from Polar.
    Includes both raw API fields and computed analytics fields.
    """
    __tablename__ = "sleep_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="polar")
    source_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    sleep_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    bedtime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    wake_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Sleep stages (seconds) — from Polar API
    light_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    deep_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    rem_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    unrecognized_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Sleep stage percentages — computed
    deep_pct: Mapped[Optional[float]] = mapped_column(Float)   # 0-100
    rem_pct: Mapped[Optional[float]] = mapped_column(Float)    # 0-100
    light_pct: Mapped[Optional[float]] = mapped_column(Float)  # 0-100

    # Polar scores
    sleep_score: Mapped[Optional[int]] = mapped_column(Integer)        # 0-100
    sleep_charge: Mapped[Optional[float]] = mapped_column(Float)       # 0-5 (Polar)
    nightly_recharge_score: Mapped[Optional[int]] = mapped_column(Integer)
    ans_charge: Mapped[Optional[float]] = mapped_column(Float)

    # Sleep architecture
    sleep_cycles: Mapped[Optional[int]] = mapped_column(Integer)
    continuity: Mapped[Optional[float]] = mapped_column(Float)         # 0-5 (Polar)
    continuity_class: Mapped[Optional[int]] = mapped_column(Integer)   # 1-5
    total_interruption_duration: Mapped[Optional[int]] = mapped_column(Integer)  # seconds

    # Cardiovascular
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer)
    nocturnal_hr_min: Mapped[Optional[int]] = mapped_column(Integer)   # lowest HR during sleep
    nocturnal_hr_dip: Mapped[Optional[float]] = mapped_column(Float)   # % drop from resting HR
    breathing_rate: Mapped[Optional[float]] = mapped_column(Float)

    # HRV
    hrv_avg_ms: Mapped[Optional[float]] = mapped_column(Float)
    hrv_rmssd: Mapped[Optional[float]] = mapped_column(Float)

    # Computed composite score (0-100)
    sleep_quality_composite: Mapped[Optional[float]] = mapped_column(Float)

    # Deep sleep deficit flag
    deep_sleep_deficit: Mapped[Optional[bool]] = mapped_column(Boolean)  # True if deep_pct < 15%

    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Daily Summary ────────────────────────────────────────────────────────────

class DailySummary(Base):
    """
    Computed daily aggregate — training load + sleep + nutrition targets.
    """
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    # PMC (Performance Management Chart)
    ctl: Mapped[Optional[float]] = mapped_column(Float)
    atl: Mapped[Optional[float]] = mapped_column(Float)
    tsb: Mapped[Optional[float]] = mapped_column(Float)

    # Training day totals
    total_tss: Mapped[Optional[float]] = mapped_column(Float)
    total_calories_burned: Mapped[Optional[float]] = mapped_column(Float)
    total_activity_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Recovery (TSB-based)
    recovery_score: Mapped[Optional[int]] = mapped_column(Integer)
    readiness_label: Mapped[Optional[str]] = mapped_column(String(20))

    # Sleep analytics cross-referenced with training
    sleep_quality_composite: Mapped[Optional[float]] = mapped_column(Float)    # 0-100
    nocturnal_hr_dip: Mapped[Optional[float]] = mapped_column(Float)           # %
    deep_sleep_deficit: Mapped[Optional[bool]] = mapped_column(Boolean)
    sleep_debt_minutes: Mapped[Optional[int]] = mapped_column(Integer)         # 7-day rolling

    # Recovery classification (TSB × Sleep matrix)
    recovery_classification: Mapped[Optional[str]] = mapped_column(String(30))
    training_recommendation: Mapped[Optional[str]] = mapped_column(String(255))

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
