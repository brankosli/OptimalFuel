// ─── Duration & distance ──────────────────────────────────────────────────────

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '—'
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

// ─── TSB / readiness colours ──────────────────────────────────────────────────

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

// ─── Recovery classification ──────────────────────────────────────────────────

export function recoveryClassColor(cls: string | null | undefined): string {
  switch (cls) {
    case 'peak':        return 'var(--accent)'
    case 'high':        return 'var(--positive)'
    case 'fresh_tired': return '#a3e635'
    case 'moderate':    return 'var(--warning)'
    case 'caution':     return '#fb923c'
    case 'low':         return 'var(--negative)'
    case 'overreach':   return '#ef4444'
    default:            return 'var(--text-muted)'
  }
}

export function recoveryClassBg(cls: string | null | undefined): string {
  switch (cls) {
    case 'peak':        return 'rgba(232,255,71,0.12)'
    case 'high':        return 'rgba(74,222,128,0.10)'
    case 'fresh_tired': return 'rgba(163,230,53,0.10)'
    case 'moderate':    return 'rgba(251,191,36,0.10)'
    case 'caution':     return 'rgba(251,146,60,0.10)'
    case 'low':         return 'rgba(248,113,113,0.10)'
    case 'overreach':   return 'rgba(239,68,68,0.15)'
    default:            return 'var(--bg-elevated)'
  }
}

export function recoveryClassLabel(cls: string | null | undefined): string {
  switch (cls) {
    case 'peak':        return 'Peak'
    case 'high':        return 'High'
    case 'fresh_tired': return 'Fresh / Tired'
    case 'moderate':    return 'Moderate'
    case 'caution':     return 'Caution'
    case 'low':         return 'Low'
    case 'overreach':   return 'Overreach Risk'
    default:            return '—'
  }
}

// ─── Sleep quality colours ────────────────────────────────────────────────────

export function sleepQualityColor(score: number | null | undefined): string {
  if (score == null) return 'var(--text-muted)'
  if (score >= 75) return 'var(--positive)'
  if (score >= 55) return 'var(--warning)'
  return 'var(--negative)'
}

export function hrDipColor(dip: number | null | undefined): string {
  if (dip == null) return 'var(--text-muted)'
  if (dip >= 10) return 'var(--positive)'
  if (dip >= 8)  return 'var(--warning)'
  return 'var(--negative)'
}

export function hrDipLabel(dip: number | null | undefined): string {
  if (dip == null) return '—'
  if (dip >= 10) return 'Healthy dip'
  if (dip >= 8)  return 'Borderline'
  return 'Non-dipping ⚠️'
}

export function deepPctColor(pct: number | null | undefined): string {
  if (pct == null) return 'var(--text-muted)'
  if (pct >= 15) return 'var(--positive)'
  if (pct >= 10) return 'var(--warning)'
  return 'var(--negative)'
}

// ─── ACWR ─────────────────────────────────────────────────────────────────────

export function acwrColor(acwr: number | null | undefined): string {
  if (acwr == null) return 'var(--text-muted)'
  if (acwr > 1.5)  return '#ef4444'
  if (acwr > 1.3)  return '#fb923c'
  if (acwr >= 0.8) return 'var(--positive)'
  return 'var(--info)'
}

export function acwrLabel(acwr: number | null | undefined): string {
  if (acwr == null) return '—'
  if (acwr > 1.5)  return 'Danger'
  if (acwr > 1.3)  return 'Caution'
  if (acwr >= 0.8) return 'Safe'
  return 'Low'
}

export function acwrBg(acwr: number | null | undefined): string {
  if (acwr == null) return 'var(--bg-elevated)'
  if (acwr > 1.5)  return 'rgba(239,68,68,0.10)'
  if (acwr > 1.3)  return 'rgba(251,146,60,0.10)'
  if (acwr >= 0.8) return 'rgba(74,222,128,0.10)'
  return 'rgba(96,165,250,0.10)'
}

export function monotonyColor(m: number | null | undefined): string {
  if (m == null) return 'var(--text-muted)'
  if (m > 2.0)  return 'var(--negative)'
  if (m > 1.5)  return 'var(--warning)'
  return 'var(--positive)'
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

// ─── Carb strategy ────────────────────────────────────────────────────────────

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
