import { useState } from 'react'
import { useActivities } from '@/hooks/useData'
import { formatDuration, formatDistance, formatPace, sportIcon, tsbColor } from '@/utils/format'
import { format, parseISO } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer,
} from 'recharts'

export default function TrainingPage() {
  const [days, setDays] = useState(30)
  const { data: activities = [], isLoading } = useActivities(days)

  // Aggregate weekly TSS for bar chart
  const weeklyTSS = buildWeeklyTSS(activities)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Training</h1>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* ── Weekly load bar chart ───────────────────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          Weekly Training Load (TSS)
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={weeklyTSS} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
              cursor={{ fill: 'var(--accent-muted)' }}
            />
            <Bar dataKey="tss" name="TSS" fill="var(--accent)" radius={[3, 3, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Activity list ───────────────────────────────── */}
      <div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
          {activities.length} activities
        </p>
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
        ) : activities.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: 'var(--space-8)' }}>
            No activities found. Sync your data to get started.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {activities.map((a: any) => (
              <ActivityCard key={a.id} activity={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ActivityCard({ activity: a }: { activity: any }) {
  const isRun = a.sport_type === 'run'
  const isRide = a.sport_type === 'ride'

  return (
    <div className="card-sm" style={{
      display: 'grid',
      gridTemplateColumns: '40px 1fr auto',
      gap: 'var(--space-4)',
      alignItems: 'center',
    }}>
      {/* Icon */}
      <div style={{ fontSize: 24, textAlign: 'center' }}>
        {sportIcon(a.sport_type)}
      </div>

      {/* Main info */}
      <div>
        <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
          {a.name ?? a.sport_type}
          <span style={{
            fontSize: 10, padding: '2px 6px',
            background: a.source === 'polar' ? 'rgba(96,165,250,0.15)' : 'rgba(251,100,48,0.15)',
            color: a.source === 'polar' ? 'var(--info)' : '#fb6430',
            borderRadius: 4, fontWeight: 500,
          }}>
            {a.source}
          </span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3, display: 'flex', gap: 'var(--space-4)' }}>
          <span>{format(parseISO(a.start_time), 'MMM d, HH:mm')}</span>
          <span>{formatDuration(a.duration_seconds)}</span>
          {a.distance_meters > 0 && <span>{formatDistance(a.distance_meters)}</span>}
          {isRun && a.distance_meters && <span>{formatPace(a.distance_meters, a.duration_seconds)}</span>}
          {a.avg_heart_rate && <span>❤️ {a.avg_heart_rate} bpm</span>}
          {isRide && a.avg_power_watts && <span>⚡ {Math.round(a.avg_power_watts)}W</span>}
        </div>
      </div>

      {/* TSS */}
      <div style={{ textAlign: 'right' }}>
        {a.tss != null ? (
          <>
            <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
              {a.tss}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>TSS</div>
          </>
        ) : a.calories ? (
          <>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
              {Math.round(a.calories)}
            </div>
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
        <button
          key={n}
          onClick={() => onChange(n)}
          style={{
            padding: '6px 12px',
            fontSize: 12,
            borderRadius: 'var(--radius-sm)',
            border: '1px solid',
            borderColor: value === n ? 'var(--accent)' : 'var(--bg-border)',
            background: value === n ? 'var(--accent-muted)' : 'var(--bg-elevated)',
            color: value === n ? 'var(--accent)' : 'var(--text-secondary)',
            fontWeight: value === n ? 500 : 400,
            transition: 'all 0.15s',
          }}
        >
          {n}d
        </button>
      ))}
    </div>
  )
}

function buildWeeklyTSS(activities: any[]): { week: string; tss: number }[] {
  const weeks: Record<string, number> = {}
  for (const a of activities) {
    if (!a.date || !a.tss) continue
    const weekStart = format(parseISO(a.date), "'W'w")
    weeks[weekStart] = (weeks[weekStart] ?? 0) + a.tss
  }
  return Object.entries(weeks)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([week, tss]) => ({ week, tss: Math.round(tss) }))
}
