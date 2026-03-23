import { useState } from 'react'
import { useSleep } from '@/hooks/useData'
import { formatSleepHours } from '@/utils/format'
import { format, parseISO } from 'date-fns'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Area,
} from 'recharts'

export default function SleepPage() {
  const [days, setDays] = useState(30)
  const { data: sleep = [], isLoading } = useSleep(days)

  const sorted = [...sleep].sort((a: any, b: any) => a.date.localeCompare(b.date))

  const chartData = sorted.map((s: any) => ({
    date: format(parseISO(s.date), 'MMM d'),
    score: s.sleep_score,
    recharge: s.nightly_recharge_score,
    hrv: s.hrv_rmssd ? Math.round(s.hrv_rmssd) : null,
    rhr: s.resting_hr,
    hours: s.total_sleep_seconds ? +(s.total_sleep_seconds / 3600).toFixed(1) : null,
    deep: s.deep_sleep_seconds ? +(s.deep_sleep_seconds / 3600).toFixed(1) : null,
    rem: s.rem_sleep_seconds ? +(s.rem_sleep_seconds / 3600).toFixed(1) : null,
    light: s.light_sleep_seconds ? +(s.light_sleep_seconds / 3600).toFixed(1) : null,
  }))

  const latest = sorted[sorted.length - 1] as any

  // Rolling averages
  const avgScore   = avg(sleep.map((s: any) => s.sleep_score))
  const avgRecharge = avg(sleep.map((s: any) => s.nightly_recharge_score))
  const avgHRV     = avg(sleep.map((s: any) => s.hrv_rmssd))
  const avgSleep   = avg(sleep.map((s: any) => s.total_sleep_seconds))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Sleep & Recovery</h1>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* ── Period averages ─────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
        <StatCard label="Avg Sleep Score"      value={avgScore?.toFixed(0) ?? '—'}  unit="/ 100" />
        <StatCard label="Avg Nightly Recharge" value={avgRecharge?.toFixed(0) ?? '—'} unit="/ 100" />
        <StatCard label="Avg HRV (RMSSD)"      value={avgHRV?.toFixed(0) ?? '—'}    unit="ms" />
        <StatCard label="Avg Sleep Duration"   value={avgSleep ? formatSleepHours(avgSleep) : '—'} />
      </div>

      {/* ── Sleep score + Nightly Recharge trend ────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          Sleep Score & Nightly Recharge
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
            <Area type="monotone" dataKey="score"    name="Sleep Score"    stroke="var(--info)"     fill="rgba(96,165,250,0.08)"  strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="recharge" name="Nightly Recharge" stroke="var(--positive)" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── HRV + RHR ───────────────────────────────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          HRV (RMSSD) & Resting Heart Rate
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis yAxisId="hrv" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="rhr" orientation="right" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
            <Line yAxisId="hrv" type="monotone" dataKey="hrv" name="HRV ms"  stroke="var(--accent)"   strokeWidth={2} dot={false} connectNulls />
            <Line yAxisId="rhr" type="monotone" dataKey="rhr" name="RHR bpm" stroke="var(--negative)" strokeWidth={2} dot={false} connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── Sleep stage breakdown ────────────────────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          Sleep Stage Breakdown (hours)
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="deep"  name="Deep"  fill="var(--info)"     stackId="a" maxBarSize={16} />
            <Bar dataKey="rem"   name="REM"   fill="var(--accent)"   stackId="a" maxBarSize={16} />
            <Bar dataKey="light" name="Light" fill="var(--bg-border)" stackId="a" maxBarSize={16} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

    </div>
  )
}

function StatCard({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="card-sm">
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{value}</span>
        {unit && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{unit}</span>}
      </div>
    </div>
  )
}

function RangePicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {[14, 30, 60].map(n => (
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

function avg(values: (number | null | undefined)[]): number | null {
  const valid = values.filter(v => v != null) as number[]
  if (!valid.length) return null
  return valid.reduce((a, b) => a + b, 0) / valid.length
}
