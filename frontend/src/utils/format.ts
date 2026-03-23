// ─── Formatting ───────────────────────────────────────────────────────────────

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function formatDistance(meters: number | null | undefined): string {
  if (!meters) return '—'
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`
  return `${Math.round(meters)} m`
}

export function formatPace(meters: number, seconds: number): string {
  if (!meters || !seconds) return '—'
  const pace_s_per_km = seconds / (meters / 1000)
  const min = Math.floor(pace_s_per_km / 60)
  const sec = Math.round(pace_s_per_km % 60)
  return `${min}:${sec.toString().padStart(2, '0')} /km`
}

export function formatSleepHours(seconds: number | null | undefined): string {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

export function formatCalories(cal: number | null | undefined): string {
  if (!cal) return '—'
  return `${Math.round(cal)} kcal`
}

// ─── TSB / readiness colour coding ────────────────────────────────────────────

export function tsbColor(tsb: number | null | undefined): string {
  if (tsb == null) return 'var(--text-muted)'
  if (tsb >= 10)  return 'var(--positive)'
  if (tsb >= -5)  return 'var(--warning)'
  return 'var(--negative)'
}

export function readinessColor(label: string | null | undefined): string {
  switch (label) {
    case 'peak':     return 'var(--accent)'
    case 'high':     return 'var(--positive)'
    case 'moderate': return 'var(--warning)'
    case 'low':      return 'var(--negative)'
    default:         return 'var(--text-muted)'
  }
}

export function readinessBg(label: string | null | undefined): string {
  switch (label) {
    case 'peak':     return 'rgba(232, 255, 71, 0.1)'
    case 'high':     return 'rgba(74, 222, 128, 0.1)'
    case 'moderate': return 'rgba(251, 191, 36, 0.1)'
    case 'low':      return 'rgba(248, 113, 113, 0.1)'
    default:         return 'var(--bg-elevated)'
  }
}

// ─── Sport icons ──────────────────────────────────────────────────────────────

export function sportIcon(sport: string): string {
  const icons: Record<string, string> = {
    run: '🏃', ride: '🚴', swim: '🏊', strength: '🏋️',
    yoga: '🧘', hike: '🥾', rowing: '🚣', walk: '🚶',
    crosstraining: '⚡', ski: '⛷️', soccer: '⚽', workout: '💪',
  }
  return icons[sport?.toLowerCase()] ?? '🏅'
}

// ─── Carb strategy label ──────────────────────────────────────────────────────

export function carbStrategyLabel(strategy: string | null | undefined): string {
  switch (strategy) {
    case 'high':     return 'High Carb Day'
    case 'moderate': return 'Moderate Carb Day'
    case 'low':      return 'Low Carb Day'
    default:         return '—'
  }
}

export function carbStrategyColor(strategy: string | null | undefined): string {
  switch (strategy) {
    case 'high':     return 'var(--accent)'
    case 'moderate': return 'var(--warning)'
    case 'low':      return 'var(--info)'
    default:         return 'var(--text-muted)'
  }
}
