import { useTodaySummary, useActivities, useSleep } from '@/hooks/useData'
import {
  tsbColor, carbStrategyLabel, carbStrategyColor,
  formatDuration, formatCalories, sportIcon,
  recoveryClassColor, recoveryClassBg, recoveryClassLabel,
  sleepQualityColor, hrDipColor, hrDipLabel, deepPctColor,
} from '@/utils/format'
import { format } from 'date-fns'
import PMCChart from '@/components/charts/PMCChart'

// ─── Readiness score colour ───────────────────────────────────────────────────
function readinessScoreColor(score: number | null | undefined): string {
  if (score == null) return 'var(--text-muted)'
  if (score >= 75) return 'var(--positive)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--negative)'
}

function intensityColor(intensity: string | undefined): string {
  switch (intensity) {
    case 'threshold': return 'var(--accent)'
    case 'tempo':     return '#fb923c'
    case 'zone2':     return 'var(--positive)'
    case 'zone1':     return 'var(--info)'
    case 'rest':      return 'var(--text-muted)'
    default:          return 'var(--text-muted)'
  }
}

function sportEmoji(sport: string | undefined): string {
  const map: Record<string, string> = {
    run: '🏃', ride: '🚴', strength: '🏋️',
    swim: '🏊', walk: '🚶', rest: '😴',
  }
  return map[sport ?? ''] ?? '🏅'
}

export default function DashboardPage() {
  const { data: today, isLoading } = useTodaySummary()
  const { data: activities = [] } = useActivities(7)
  const { data: sleep = [] } = useSleep(1)

  const todaySleep = sleep[0]
  const rec = today?.recommendation
  const todayActivities = activities.filter(
    (a: any) => a.date === format(new Date(), 'yyyy-MM-dd')
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600 }}>
            {format(new Date(), 'EEEE, MMMM d')}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
            Training & nutrition overview
          </p>
        </div>
        <SyncButton />
      </div>

      {/* ── Row 1: Readiness Score + Fuel + Sleep ────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)' }}>

        {/* Readiness score card */}
        <div className="card" style={{
          background: recoveryClassBg(today?.recovery_classification),
          borderColor: recoveryClassColor(today?.recovery_classification),
        }}>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
            letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Readiness
          </p>
          {isLoading ? <Skeleton /> : (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <span style={{ fontSize: 48, fontWeight: 800, lineHeight: 1,
                  color: readinessScoreColor(rec?.readiness_score) }}>
                  {rec?.readiness_score ?? '—'}
                </span>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>/ 100</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 600,
                color: recoveryClassColor(today?.recovery_classification), marginTop: 4 }}>
                {recoveryClassLabel(today?.recovery_classification)}
              </div>
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-4)' }}>
                <Metric label="CTL" value={today?.ctl?.toFixed(1) ?? '—'} />
                <Metric label="ATL" value={today?.atl?.toFixed(1) ?? '—'} />
                <Metric label="TSB" value={today?.tsb?.toFixed(1) ?? '—'}
                  valueColor={tsbColor(today?.tsb)} />
              </div>
            </>
          )}
        </div>

        {/* Fuel Target */}
        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
            letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Fuel Target
          </p>
          {isLoading ? <Skeleton /> : today?.target_calories ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                <span style={{ fontSize: 36, fontWeight: 600, lineHeight: 1 }}>
                  {Math.round(today.target_calories)}
                </span>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>kcal</span>
              </div>
              <div style={{ marginTop: 4, fontSize: 12, fontWeight: 500,
                color: carbStrategyColor(today.carb_strategy) }}>
                {carbStrategyLabel(today.carb_strategy)}
              </div>
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-4)' }}>
                <Metric label="Carbs"   value={`${today.target_carbs_g ?? '—'}g`}   valueColor="var(--accent)" />
                <Metric label="Protein" value={`${today.target_protein_g ?? '—'}g`} valueColor="var(--info)" />
                <Metric label="Fat"     value={`${today.target_fat_g ?? '—'}g`}     valueColor="var(--warning)" />
              </div>
            </>
          ) : (
            <NoData message="Set up your profile to see targets" />
          )}
        </div>

        {/* Sleep */}
        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
            letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Last Night's Sleep
          </p>
          {todaySleep ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontSize: 32, fontWeight: 700, lineHeight: 1,
                  color: sleepQualityColor(todaySleep.sleep_quality_composite) }}>
                  {todaySleep.sleep_quality_composite?.toFixed(0) ?? todaySleep.sleep_score ?? '—'}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {todaySleep.sleep_quality_composite ? 'quality' : '/ 100'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, display: 'flex', gap: 12 }}>
                {todaySleep.total_sleep_seconds && <span>{formatDuration(todaySleep.total_sleep_seconds)}</span>}
                {todaySleep.sleep_cycles && <span>{todaySleep.sleep_cycles} cycles</span>}
              </div>
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
                <Metric label="Deep" value={todaySleep.deep_pct ? `${todaySleep.deep_pct.toFixed(0)}%` : '—'}
                  valueColor={deepPctColor(todaySleep.deep_pct)} />
                <Metric label="REM" value={todaySleep.rem_pct ? `${todaySleep.rem_pct.toFixed(0)}%` : '—'}
                  valueColor="var(--info)" />
                <Metric label="HR Dip" value={todaySleep.nocturnal_hr_dip ? `${todaySleep.nocturnal_hr_dip.toFixed(0)}%` : '—'}
                  valueColor={hrDipColor(todaySleep.nocturnal_hr_dip)} />
              </div>
              {today?.sleep_debt_minutes != null && today.sleep_debt_minutes > 0 && (
                <div style={{
                  marginTop: 'var(--space-3)', fontSize: 11,
                  color: today.sleep_debt_minutes > 120 ? 'var(--negative)' : 'var(--warning)',
                  background: today.sleep_debt_minutes > 120 ? 'rgba(248,113,113,0.08)' : 'rgba(251,191,36,0.08)',
                  padding: '4px 8px', borderRadius: 4,
                }}>
                  7-day sleep debt: {Math.floor(today.sleep_debt_minutes / 60)}h {today.sleep_debt_minutes % 60}m
                </div>
              )}
            </>
          ) : (
            <NoData message="No sleep data for last night" />
          )}
        </div>
      </div>

      {/* ── Training Recommendation Card ─────────────── */}
      {rec && !rec.error && (
        <div className="card" style={{ borderColor: intensityColor(rec.intensity) + '60' }}>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
            letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
            Today's Training Recommendation
          </p>

          {/* Headline row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
            <span style={{ fontSize: 36 }}>{sportEmoji(rec.sport)}</span>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: intensityColor(rec.intensity) }}>
                {rec.headline}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {rec.intensity_label}
              </div>
            </div>
            {rec.sport !== 'rest' && (
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 'var(--space-5)' }}>
                <Metric label="Duration"  value={`${rec.duration_min} min`} />
                {rec.hr_min && rec.hr_max && (
                  <Metric label="HR Target" value={`${rec.hr_min}–${rec.hr_max}`} valueColor="var(--negative)" />
                )}
                {rec.tss_target > 0 && (
                  <Metric label="Est. TSS" value={rec.tss_target} />
                )}
              </div>
            )}
          </div>

          {/* Detail paragraph */}
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7,
            padding: 'var(--space-4)', background: 'var(--bg-base)',
            borderRadius: 'var(--radius-sm)', margin: 0 }}>
            {rec.detail}
          </p>

          {/* Warnings */}
          {rec.warnings?.length > 0 && (
            <div style={{ marginTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {rec.warnings.map((w: string, i: number) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 12, color: '#fb923c',
                  background: 'rgba(251,146,60,0.08)',
                  padding: '6px 10px', borderRadius: 4,
                }}>
                  <span>⚠️</span> {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Sleep architecture detail ─────────────────── */}
      {todaySleep?.deep_pct != null && (
        <div className="card" style={{ padding: 'var(--space-5)' }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)',
            marginBottom: 'var(--space-4)', textTransform: 'uppercase', letterSpacing: 1 }}>
            Sleep Architecture — last night
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-4)' }}>
            <SleepMetric label="Deep Sleep"
              value={todaySleep.deep_pct?.toFixed(0) + '%'} target="Target: ≥15%"
              color={deepPctColor(todaySleep.deep_pct)}
              alert={todaySleep.deep_sleep_deficit} alertText="Deficit — physical recovery impaired" />
            <SleepMetric label="REM Sleep"
              value={todaySleep.rem_pct?.toFixed(0) + '%'} target="Target: ≥20%"
              color="var(--info)" />
            <SleepMetric label="Continuity"
              value={todaySleep.continuity?.toFixed(1) + '/5'} target="Fragmentation score"
              color={todaySleep.continuity >= 3.5 ? 'var(--positive)' : todaySleep.continuity >= 2.5 ? 'var(--warning)' : 'var(--negative)'} />
            <SleepMetric label="Nocturnal HR Dip"
              value={todaySleep.nocturnal_hr_dip?.toFixed(0) + '%'}
              target={hrDipLabel(todaySleep.nocturnal_hr_dip)}
              color={hrDipColor(todaySleep.nocturnal_hr_dip)}
              alert={todaySleep.nocturnal_hr_dip != null && todaySleep.nocturnal_hr_dip < 8}
              alertText="Non-dipping — elevated sympathetic tone" />
            <SleepMetric label="Sleep Cycles"
              value={todaySleep.sleep_cycles?.toString() ?? '—'} target="Target: 4-6 cycles"
              color={todaySleep.sleep_cycles >= 4 ? 'var(--positive)' : 'var(--warning)'} />
          </div>
        </div>
      )}

      {/* ── PMC Chart ────────────────────────────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 'var(--space-5)',
          color: 'var(--text-secondary)' }}>
          Performance Management Chart — last 90 days
        </p>
        <PMCChart />
      </div>

      {/* ── Today's activities ────────────────────────── */}
      {todayActivities.length > 0 && (
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)',
            marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: 1 }}>
            Today's Sessions
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {todayActivities.map((a: any) => <ActivityRow key={a.id} activity={a} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Metric({ label, value, valueColor }: { label: string; value: any; valueColor?: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, fontFamily: 'var(--font-mono)',
        color: valueColor ?? 'var(--text-primary)', marginTop: 1 }}>
        {value}
      </div>
    </div>
  )
}

function SleepMetric({ label, value, target, color, alert, alertText }: any) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)', color }}>{value}</div>
      <div style={{ fontSize: 10, color: alert ? color : 'var(--text-muted)', marginTop: 3, lineHeight: 1.4 }}>
        {alert ? alertText : target}
      </div>
    </div>
  )
}

function ActivityRow({ activity: a }: { activity: any }) {
  return (
    <div className="card-sm" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
      <span style={{ fontSize: 20 }}>{sportIcon(a.sport_type)}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 500 }}>{a.name ?? a.sport_type}</div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
          {formatDuration(a.duration_seconds)} · {a.avg_heart_rate ? `${a.avg_heart_rate} bpm` : ''} · {a.source}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
          {a.tss ? `${a.tss} TSS` : formatCalories(a.calories)}
        </div>
      </div>
    </div>
  )
}

function NoData({ message }: { message: string }) {
  return <div style={{ color: 'var(--text-muted)', fontSize: 13, paddingTop: 'var(--space-2)' }}>{message}</div>
}

function Skeleton() {
  return <div style={{ height: 60, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', opacity: 0.6 }} />
}

function SyncButton() {
  return (
    <button
      onClick={() => fetch('/api/v1/analytics/sync', { method: 'POST' })}
      style={{
        padding: '8px 16px', background: 'var(--bg-elevated)',
        border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)',
        color: 'var(--text-secondary)', fontSize: 13,
        display: 'flex', alignItems: 'center', gap: 6,
      }}
    >
      ↻ Sync now
    </button>
  )
}
