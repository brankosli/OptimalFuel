import { useTodaySummary, useActivities, useSleep } from '@/hooks/useData'
import { readinessColor, readinessBg, tsbColor, carbStrategyLabel, carbStrategyColor, formatDuration, formatCalories, sportIcon } from '@/utils/format'
import { format } from 'date-fns'
import PMCChart from '@/components/charts/PMCChart'
import MacroRing from '@/components/nutrition/MacroRing'

export default function DashboardPage() {
  const { data: today, isLoading } = useTodaySummary()
  const { data: activities = [] } = useActivities(7)
  const { data: sleep = [] } = useSleep(1)

  const todaySleep = sleep[0]
  const todayActivities = activities.filter(
    (a: any) => a.date === format(new Date(), 'yyyy-MM-dd')
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      {/* ── Header ────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary)' }}>
            {format(new Date(), 'EEEE, MMMM d')}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
            Your training & nutrition overview
          </p>
        </div>
        <SyncButton />
      </div>

      {/* ── Top row: Readiness + Macros + PMC snapshot ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)' }}>

        {/* Readiness card */}
        <div className="card" style={{
          background: readinessBg(today?.readiness_label),
          borderColor: readinessColor(today?.readiness_label),
        }}>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Today's Readiness
          </p>
          {isLoading ? <Skeleton /> : (
            <>
              <div style={{ fontSize: 36, fontWeight: 600, color: readinessColor(today?.readiness_label), lineHeight: 1 }}>
                {today?.recovery_score ?? '—'}
              </div>
              <div style={{ fontSize: 13, color: readinessColor(today?.readiness_label), marginTop: 4, textTransform: 'capitalize' }}>
                {today?.readiness_label ?? 'No data'}
              </div>
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-4)' }}>
                <Metric label="CTL" value={today?.ctl?.toFixed(1) ?? '—'} />
                <Metric label="ATL" value={today?.atl?.toFixed(1) ?? '—'} />
                <Metric label="TSB" value={today?.tsb?.toFixed(1) ?? '—'} valueColor={tsbColor(today?.tsb)} />
              </div>
            </>
          )}
        </div>

        {/* Nutrition targets card */}
        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Fuel Target
          </p>
          {isLoading ? <Skeleton /> : today?.target_calories ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                <span style={{ fontSize: 36, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1 }}>
                  {Math.round(today.target_calories)}
                </span>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>kcal</span>
              </div>
              <div style={{
                marginTop: 4, fontSize: 12, fontWeight: 500,
                color: carbStrategyColor(today.carb_strategy),
              }}>
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

        {/* Last night's sleep */}
        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Last Night's Sleep
          </p>
          {todaySleep ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                <span style={{ fontSize: 36, fontWeight: 600, lineHeight: 1 }}>
                  {todaySleep.sleep_score ?? '—'}
                </span>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>/ 100</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                {formatDuration(todaySleep.total_sleep_seconds)} total
              </div>
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-4)' }}>
                <Metric label="Recharge" value={todaySleep.nightly_recharge_score ?? '—'} />
                <Metric label="HRV"      value={todaySleep.hrv_rmssd ? `${Math.round(todaySleep.hrv_rmssd)}ms` : '—'} />
                <Metric label="RHR"      value={todaySleep.resting_hr ? `${todaySleep.resting_hr}bpm` : '—'} />
              </div>
            </>
          ) : (
            <NoData message="No sleep data for last night" />
          )}
        </div>
      </div>

      {/* ── PMC Chart ─────────────────────────────────────── */}
      <div className="card" style={{ padding: 'var(--space-6)' }}>
        <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 'var(--space-5)', color: 'var(--text-secondary)' }}>
          Performance Management Chart — last 90 days
        </p>
        <PMCChart />
      </div>

      {/* ── Today's activities ────────────────────────────── */}
      {todayActivities.length > 0 && (
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: 1 }}>
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
      <div style={{ fontSize: 15, fontWeight: 600, fontFamily: 'var(--font-mono)', color: valueColor ?? 'var(--text-primary)', marginTop: 1 }}>
        {value}
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
          {formatDuration(a.duration_seconds)} · {a.avg_heart_rate ? `${a.avg_heart_rate} bpm avg` : ''} · {a.source}
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
  return (
    <div style={{ color: 'var(--text-muted)', fontSize: 13, paddingTop: 'var(--space-2)' }}>
      {message}
    </div>
  )
}

function Skeleton() {
  return <div style={{ height: 60, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', opacity: 0.6 }} />
}

function SyncButton() {
  return (
    <button
      onClick={() => fetch('/api/v1/analytics/sync', { method: 'POST' })}
      style={{
        padding: '8px 16px',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--text-secondary)',
        fontSize: 13,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        transition: 'all 0.15s',
      }}
    >
      ↻ Sync now
    </button>
  )
}
