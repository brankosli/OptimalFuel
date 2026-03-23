// ─── Activities ───────────────────────────────────────────────────────────────

export interface Activity {
  id: number
  source: 'polar' | 'strava'
  source_id: string
  activity_date: string        // ISO date string
  start_time: string           // ISO datetime
  duration_seconds: number
  sport_type: string
  name: string | null
  calories: number | null
  distance_meters: number | null
  elevation_gain_meters: number | null
  avg_heart_rate: number | null
  max_heart_rate: number | null
  training_load: number | null
  tss: number | null
  avg_power_watts: number | null
  normalized_power_watts: number | null
}

// ─── Sleep ────────────────────────────────────────────────────────────────────

export interface SleepRecord {
  id: number
  sleep_date: string
  total_sleep_seconds: number | null
  deep_sleep_seconds: number | null
  rem_sleep_seconds: number | null
  light_sleep_seconds: number | null
  sleep_score: number | null
  nightly_recharge_score: number | null
  ans_charge: number | null
  hrv_rmssd: number | null
  resting_hr: number | null
}

// ─── Analytics / PMC ──────────────────────────────────────────────────────────

export interface DailySummary {
  summary_date: string
  ctl: number | null           // Chronic Training Load (fitness)
  atl: number | null           // Acute Training Load (fatigue)
  tsb: number | null           // Training Stress Balance (form)
  total_tss: number | null
  total_calories_burned: number | null
  recovery_score: number | null
  readiness_label: 'low' | 'moderate' | 'high' | 'peak' | null
  target_calories: number | null
  target_carbs_g: number | null
  target_protein_g: number | null
  target_fat_g: number | null
  carb_strategy: 'high' | 'moderate' | 'low' | null
}

// ─── Nutrition ────────────────────────────────────────────────────────────────

export interface MealLog {
  id: number
  log_date: string
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  calories: number | null
  carbs_g: number | null
  protein_g: number | null
  fat_g: number | null
  notes: string | null
}

// ─── User Profile ─────────────────────────────────────────────────────────────

export interface UserProfile {
  weight_kg: number | null
  height_cm: number | null
  age: number | null
  sex: 'male' | 'female' | null
  ftp_watts: number | null
  lthr_bpm: number | null
  vo2max: number | null
  dietary_preference: string | null
  protein_target_per_kg: number
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthStatus {
  polar: { connected: boolean; last_sync?: string }
  strava: { connected: boolean; last_sync?: string }
}
