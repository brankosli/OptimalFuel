import { useState } from 'react'
import { useActivities, usePMC } from '@/hooks/useData'
import { formatDuration, formatDistance, formatPace, sportIcon, formatCalories } from '@/utils/format'
import { format, parseISO, subDays } from 'date-fns'
import {
  ComposedChart, BarChart, Bar, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

// ─── ACWR helpers ─────────────────────────────────────────────────────────────

function acwrColor(acwr: number | null | undefined): string {
  if (acwr == null) return 'var(--text-muted)'
  if (acwr > 1.5)  return '#ef4444'   // danger — red
  if (acwr > 1.3)  return '#fb923c'   // caution — orange
  if (acwr >= 0.8) return 'var(--positive)'  // safe — green
  return 'var(--info)'                 // low — blue (detraining)
}

function acwrLabel(acwr: number | null | undefined): string {
  if (acwr == null) return '—'
  if (acwr > 1.5)  return 'Danger'
  if (acwr > 1.3)  return 'Caution'
  if (acwr >= 0.8) return 'Safe'
  return 'Low'
}

function acwrBg(acwr: number | null | undefined): string {
  if (acwr == null) return 'var(--bg-elevated)'
  if (acwr > 1.5)  return 'rgba(239,68,68,0.10)'
  if (acwr > 1.3)  return 'rgba(251,146,60,0.10)'
  if (acwr >= 0.8) return 'rgba(74,222,128,0.10)'
  return 'rgba(96,165,250,0.10)'
}

function monotonyColor(m: number | null | undefined): string {
  if (m == null) return 'var(--text-muted)'
  if (m > 2.0)  return 'var(--negative)'
  if (m > 1.5)  return 'var(--warning)'
  return 'var(--positive)'
}

export default function TrainingPage() {
  const [days, setDays] = useState(30)
  const { data: activities = [], isLoading } = useActivities(days)
  const { data: pmcData = [] } = usePMC(days)

  // Latest PMC values for metric cards
  const latest = pmcData.length ? pmcData[pmcData.length - 1] : null

  // Weekly TSS for bar chart
  const weeklyTSS = buildWeeklyTSS(activities)

  // ACWR trend from PMC data
  const acwrTrend = pmcData
    .filter((d: any) => d.acwr != null)
    .map((d: any) => ({
      date: d.date.slice(5),
      acwr: d.acwr,
      fill: d.acwr > 1.3 ? '#ef4444' : d.acwr < 0.8 ? '#60a5fa' : '#4ade80',
    }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Training</h1>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* ── Metric cards: ACWR + Monotony + Strain ──── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)' }}>

        {/* ACWR card */}
        <div className="card" style={{
          background: acwrBg(latest?.acwr),
          borderColor: acwrColor(latest?.acwr),
        }}>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            ACWR — Injury Risk
          </p>
          <div style={{ fontSize: 36, fontWeight: 700, color: acwrColor(latest?.acwr), lineHeight: 1 }}>
            {latest?.acwr?.toFixed(2) ?? '—'}
          </div>
          <div style={{ fontSize: 12, color: acwrColor(latest?.acwr), marginTop: 4, fontWeight: 500 }}>
            {acwrLabel(latest?.acwr)}
          </div>
          <div style={{ marginTop: 'var(--space-4)', fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            Safe zone: 0.8 – 1.3<br />
            &gt;1.3 spike risk · &lt;0.8 detraining
          </div>
        </div>

        {/* Training Monotony */}
        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Training Monotony
          </p>
          <div style={{ fontSize: 36, fontWeight: 700, color: monotonyColor(latest?.training_monotony), lineHeight: 1 }}>
            {latest?.training_monotony?.toFixed(2) ?? '—'}
          </div>
          <div style={{ fontSize: 12, color: monotonyColor(latest?.training_monotony), marginTop: 4, fontWeight: 500 }}>
            {latest?.training_monotony == null ? '—'
              : latest.training_monotony > 2.0 ? 'Too monotonous'
              : latest.training_monotony > 1.5 ? 'Moderate variety'
              : 'Good variety'}
          </div>
          <div style={{ marginTop: 'var(--space-4)', fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            Ideal: 1.0 – 1.5<br />
            &gt;2.0 overtraining risk (Foster 1998)
          </div>
        </div>

        {/* This week TSS + CTL */}
        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Current Fitness (CTL)
          </p>
          <div style={{ fontSize: 36, fontWeight: 700, color: 'var(--positive)', lineHeight: 1 }}>
            {latest?.ctl?.toFixed(0) ?? '—'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Chronic Training Load
          </div>
          <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-4)' }}>
            <SmallMetric label="ATL" value={latest?.atl?.toFixed(0) ?? '—'} color="var(--negative)" />
            <SmallMetric label="TSB" value={latest?.tsb?.toFixed(0) ?? '—'}
              color={latest?.tsb == null ? 'var(--text-muted)' : latest.tsb >= 0 ? 'var(--positive)' : 'var(--warning)'} />
            <SmallMetric label="Strain" value={latest?.training_strain?.toFixed(0) ?? '—'} />
          </div>
        </div>
      </div>

      {/* ── ACWR trend chart ─────────────────────────── */}
      {acwrTrend.length > 0 && (
        <div className="card">
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>
            Acute:Chronic Workload Ratio — injury risk trend
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
            Green = safe (0.8-1.3) · Orange = caution (&gt;1.3) · Red = danger (&gt;1.5) · Blue = detraining (&lt;0.8)
          </p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={acwrTrend} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false}
                interval={Math.floor(acwrTrend.length / 7)} />
              <YAxis domain={[0, 2]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [v.toFixed(2), 'ACWR']} />
              <ReferenceLine y={1.3} stroke="#fb923c" strokeDasharray="3 3"
                label={{ value: '1.3', fill: '#fb923c', fontSize: 9, position: 'insideTopRight' }} />
              <ReferenceLine y={0.8} stroke="var(--info)" strokeDasharray="3 3"
                label={{ value: '0.8', fill: 'var(--info)', fontSize: 9, position: 'insideBottomRight' }} />
              <Bar dataKey="acwr" maxBarSize={12} radius={[2, 2, 0, 0]}>
                {acwrTrend.map((entry: any, i: number) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Weekly TSS bar chart ─────────────────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          Weekly Training Load (TSS)
        </p>
        {weeklyTSS.length === 0 ? (
          <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-muted)', fontSize: 13 }}>
            No TSS data — set your LTHR in Settings to calculate training stress scores
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={weeklyTSS} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
              <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: 'var(--accent-muted)' }} />
              <Bar dataKey="tss" name="TSS" fill="var(--accent)" radius={[3, 3, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Activity list ────────────────────────────── */}
      <div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
          {activities.filter((a: any) => a.source !== 'polar_dedup').length} activities
          {activities.some((a: any) => a.source === 'polar_dedup') && (
            <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>
              ({activities.filter((a: any) => a.source === 'polar_dedup').length} Polar duplicates hidden)
            </span>
          )}
        </p>
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
        ) : activities.filter((a: any) => a.source !== 'polar_dedup').length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: 'var(--space-8)' }}>
            No activities found. Sync your data to get started.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {activities
              .filter((a: any) => a.source !== 'polar_dedup')
              .map((a: any) => <ActivityCard key={a.id} activity={a} />)}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SmallMetric({ label, value, color }: any) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-mono)', color: color ?? 'var(--text-primary)', marginTop: 1 }}>
        {value}
      </div>
    </div>
  )
}

function ActivityCard({ activity: a }: { activity: any }) {
  const isRun  = a.sport_type === 'run'
  const isRide = a.sport_type === 'ride'

  return (
    <div className="card-sm" style={{
      display: 'grid', gridTemplateColumns: '40px 1fr auto',
      gap: 'var(--space-4)', alignItems: 'center',
    }}>
      <div style={{ fontSize: 24, textAlign: 'center' }}>{sportIcon(a.sport_type)}</div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
          {a.name ?? a.sport_type}
          <span style={{
            fontSize: 10, padding: '2px 6px', borderRadius: 4, fontWeight: 500,
            background: a.source === 'polar' ? 'rgba(96,165,250,0.15)' : 'rgba(251,100,48,0.15)',
            color: a.source === 'polar' ? 'var(--info)' : '#fb6430',
          }}>
            {a.source}
          </span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3, display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
          <span>{format(parseISO(a.start_time), 'MMM d, HH:mm')}</span>
          <span>{formatDuration(a.duration_seconds)}</span>
          {a.distance_meters > 0 && <span>{formatDistance(a.distance_meters)}</span>}
          {isRun && a.distance_meters && <span>{formatPace(a.distance_meters, a.duration_seconds)}</span>}
          {a.avg_heart_rate && <span>❤️ {a.avg_heart_rate} bpm</span>}
          {isRide && a.avg_power_watts && <span>⚡ {Math.round(a.avg_power_watts)}W</span>}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        {a.tss != null ? (
          <>
            <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{a.tss}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>TSS</div>
          </>
        ) : a.calories ? (
          <>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{Math.round(a.calories)}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>kcal</div>
          </>
        ) : null}
      </div>
    </div>
  )
}

function RangePicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {[14, 30, 90].map(n => (
        <button key={n} onClick={() => onChange(n)} style={{
          padding: '6px 12px', fontSize: 12, borderRadius: 'var(--radius-sm)', border: '1px solid',
          borderColor: value === n ? 'var(--accent)' : 'var(--bg-border)',
          background: value === n ? 'var(--accent-muted)' : 'var(--bg-elevated)',
          color: value === n ? 'var(--accent)' : 'var(--text-secondary)',
          transition: 'all 0.15s',
        }}>
          {n}d
        </button>
      ))}
    </div>
  )
}

function buildWeeklyTSS(activities: any[]): { week: string; tss: number }[] {
  const weeks: Record<string, number> = {}
  for (const a of activities) {
    if (!a.date || !a.tss || a.source === 'polar_dedup') continue
    const weekStart = format(parseISO(a.date), "'W'w")
    weeks[weekStart] = (weeks[weekStart] ?? 0) + a.tss
  }
  return Object.entries(weeks)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([week, tss]) => ({ week, tss: Math.round(tss) }))
}
