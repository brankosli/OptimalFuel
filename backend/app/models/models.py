"""
SQLAlchemy ORM models — all in one file for clarity at this stage.
Split into separate files per model as the project grows.
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
    """
    Unified activity record — normalised from both Polar and Strava.
    Source-specific IDs stored separately for deduplication.
    """
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)   # "polar" | "strava"
    source_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    # Core fields
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)   # run, ride, swim, etc.
    name: Mapped[Optional[str]] = mapped_column(String(255))

    # Effort metrics
    calories: Mapped[Optional[float]] = mapped_column(Float)
    distance_meters: Mapped[Optional[float]] = mapped_column(Float)
    elevation_gain_meters: Mapped[Optional[float]] = mapped_column(Float)

    # Heart rate
    avg_heart_rate: Mapped[Optional[int]] = mapped_column(Integer)
    max_heart_rate: Mapped[Optional[int]] = mapped_column(Integer)

    # Training load
    training_load: Mapped[Optional[float]] = mapped_column(Float)    # Polar's own score
    suffer_score: Mapped[Optional[int]] = mapped_column(Integer)      # Strava's suffer score
    tss: Mapped[Optional[float]] = mapped_column(Float)               # Computed TSS (Training Stress Score)

    # Power (cycling)
    avg_power_watts: Mapped[Optional[float]] = mapped_column(Float)
    normalized_power_watts: Mapped[Optional[float]] = mapped_column(Float)
    ftp_watts: Mapped[Optional[float]] = mapped_column(Float)         # FTP at time of activity

    # Raw data blob (for future use)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Sleep ────────────────────────────────────────────────────────────────────

class SleepRecord(Base):
    """
    Nightly sleep data from Polar.
    One record per night.
    """
    __tablename__ = "sleep_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="polar")
    source_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    sleep_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    bedtime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    wake_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Sleep stages (seconds)
    light_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    deep_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    rem_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Polar-specific scores (0-100)
    sleep_score: Mapped[Optional[int]] = mapped_column(Integer)
    nightly_recharge_score: Mapped[Optional[int]] = mapped_column(Integer)
    ans_charge: Mapped[Optional[float]] = mapped_column(Float)        # ANS recharge component
    sleep_charge: Mapped[Optional[float]] = mapped_column(Float)      # Sleep charge component

    # HRV
    hrv_avg_ms: Mapped[Optional[float]] = mapped_column(Float)
    hrv_rmssd: Mapped[Optional[float]] = mapped_column(Float)

    # Resting HR
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer)
    breathing_rate: Mapped[Optional[float]] = mapped_column(Float)

    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Daily Summary ────────────────────────────────────────────────────────────

class DailySummary(Base):
    """
    Computed daily aggregate — training load metrics + nutrition targets.
    Recalculated each night after all data is synced.
    """
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    # Training load (Performance Management Chart values)
    ctl: Mapped[Optional[float]] = mapped_column(Float)    # Chronic Training Load (fitness)
    atl: Mapped[Optional[float]] = mapped_column(Float)    # Acute Training Load (fatigue)
    tsb: Mapped[Optional[float]] = mapped_column(Float)    # Training Stress Balance (form)

    # Day's totals
    total_tss: Mapped[Optional[float]] = mapped_column(Float)
    total_calories_burned: Mapped[Optional[float]] = mapped_column(Float)
    total_activity_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Recovery
    recovery_score: Mapped[Optional[int]] = mapped_column(Integer)   # 0-100, computed
    readiness_label: Mapped[Optional[str]] = mapped_column(String(20))  # "low"|"moderate"|"high"|"peak"

    # Nutrition targets (computed from training load + recovery)
    target_calories: Mapped[Optional[float]] = mapped_column(Float)
    target_carbs_g: Mapped[Optional[float]] = mapped_column(Float)
    target_protein_g: Mapped[Optional[float]] = mapped_column(Float)
    target_fat_g: Mapped[Optional[float]] = mapped_column(Float)
    carb_strategy: Mapped[Optional[str]] = mapped_column(String(20))  # "high"|"moderate"|"low"

    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Nutrition Log ────────────────────────────────────────────────────────────

class MealLog(Base):
    """
    Optional — manual food/meal logging.
    """
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))   # breakfast|lunch|dinner|snack
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    calories: Mapped[Optional[float]] = mapped_column(Float)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float)
    protein_g: Mapped[Optional[float]] = mapped_column(Float)
    fat_g: Mapped[Optional[float]] = mapped_column(Float)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── User Profile ─────────────────────────────────────────────────────────────

class UserProfile(Base):
    """
    Personal baseline data for nutrition calculations.
    Single row — this is a personal app.
    """
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Body metrics
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    height_cm: Mapped[Optional[float]] = mapped_column(Float)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    sex: Mapped[Optional[str]] = mapped_column(String(10))   # "male" | "female"

    # Performance baselines
    ftp_watts: Mapped[Optional[float]] = mapped_column(Float)    # Functional Threshold Power
    lthr_bpm: Mapped[Optional[int]] = mapped_column(Integer)     # Lactate Threshold HR
    vo2max: Mapped[Optional[float]] = mapped_column(Float)       # From Polar/Garmin estimate

    # Nutrition preferences
    dietary_preference: Mapped[Optional[str]] = mapped_column(String(50))  # omnivore|vegetarian|vegan
    protein_target_per_kg: Mapped[float] = mapped_column(Float, default=1.8)  # g/kg body weight

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
