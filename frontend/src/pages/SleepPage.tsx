import { useState } from 'react'
import { useSleepInsights } from '@/hooks/useData'
import { formatSleepHours, sleepQualityColor, hrDipColor, hrDipLabel, deepPctColor } from '@/utils/format'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine, Area,
} from 'recharts'

export default function SleepPage() {
  const [days, setDays] = useState(30)
  const { data, isLoading } = useSleepInsights(days)

  const records = data?.records ?? []
  const agg = data?.aggregates ?? {}

  const chartData = records.map((s: any) => ({
    date: s.date.slice(5),   // MM-DD
    quality: s.sleep_quality_composite,
    score: s.sleep_score,
    deep: s.deep_pct,
    rem: s.rem_pct,
    light: s.light_pct,
    hours: s.total_hours,
    hr_dip: s.nocturnal_hr_dip,
    rhr: s.resting_hr,
    continuity: s.continuity ? +(s.continuity / 5 * 100).toFixed(0) : null,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Sleep & Recovery</h1>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* Period summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
        <StatCard
          label="Avg Quality Score"
          value={agg.avg_quality_score?.toFixed(0) ?? '—'}
          unit="/ 100"
          color={sleepQualityColor(agg.avg_quality_score)}
        />
        <StatCard
          label="Avg Deep Sleep"
          value={agg.avg_deep_pct?.toFixed(0) ?? '—'}
          unit="%"
          color={deepPctColor(agg.avg_deep_pct)}
          note={agg.deep_deficit_days > 0 ? `${agg.deep_deficit_days} deficit nights` : undefined}
        />
        <StatCard
          label="Avg HR Dip"
          value={agg.avg_nocturnal_hr_dip?.toFixed(0) ?? '—'}
          unit="%"
          color={hrDipColor(agg.avg_nocturnal_hr_dip)}
          note={hrDipLabel(agg.avg_nocturnal_hr_dip)}
        />
        <StatCard
          label="Avg Duration"
          value={agg.avg_hours?.toFixed(1) ?? '—'}
          unit="hrs"
          color={agg.avg_hours >= 7 ? 'var(--positive)' : agg.avg_hours >= 6 ? 'var(--warning)' : 'var(--negative)'}
        />
      </div>

      {/* Quality composite + sleep score trend */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          Sleep Quality Composite Score
          <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--text-muted)' }}>
            (deep 35% · REM 20% · continuity 25% · duration 20%)
          </span>
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
            <ReferenceLine y={65} stroke="var(--text-muted)" strokeDasharray="3 3" label={{ value: 'Good', fill: 'var(--text-muted)', fontSize: 10 }} />
            <Area type="monotone" dataKey="quality" name="Quality Score" stroke="var(--accent)" fill="var(--accent-muted)" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="score" name="Polar Score" stroke="var(--info)" strokeWidth={1.5} strokeDasharray="4 2" dot={false} connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Sleep stage % breakdown */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-5)' }}>
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>
            Sleep Stage Breakdown (%)
          </p>
          <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 11 }}>
            <span style={{ color: 'var(--info)' }}>■ Deep</span>
            <span style={{ color: 'var(--accent)' }}>■ REM</span>
            <span style={{ color: 'var(--bg-border)' }}>■ Light</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
              formatter={(v: number) => [`${v?.toFixed(0)}%`]} />
            {/* 15% reference line for deep sleep target */}
            <ReferenceLine y={15} stroke="var(--info)" strokeDasharray="3 3"
              label={{ value: '15% deep target', fill: 'var(--info)', fontSize: 9, position: 'insideTopRight' }} />
            <Bar dataKey="deep"  name="Deep %"  fill="var(--info)"     stackId="a" maxBarSize={14} />
            <Bar dataKey="rem"   name="REM %"   fill="var(--accent)"   stackId="a" maxBarSize={14} />
            <Bar dataKey="light" name="Light %" fill="var(--bg-border)" stackId="a" maxBarSize={14} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Nocturnal HR Dip */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>
          Nocturnal HR Dip
        </p>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
          % drop in HR during sleep vs resting HR. Healthy: ≥10%. Non-dipping (&lt;8%) signals elevated sympathetic tone / stress.
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
              formatter={(v: number) => [`${v?.toFixed(1)}%`]} />
            <ReferenceLine y={10} stroke="var(--positive)" strokeDasharray="3 3"
              label={{ value: 'Healthy ≥10%', fill: 'var(--positive)', fontSize: 9, position: 'insideTopRight' }} />
            <ReferenceLine y={8} stroke="var(--warning)" strokeDasharray="3 3"
              label={{ value: 'Borderline 8%', fill: 'var(--warning)', fontSize: 9, position: 'insideTopLeft' }} />
            <Bar dataKey="hr_dip" name="HR Dip %"
              fill="var(--info)" maxBarSize={14} radius={[2, 2, 0, 0]}
              label={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Resting HR + continuity */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 'var(--space-5)' }}>
          Resting HR & Sleep Continuity (% of max)
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 7)} />
            <YAxis yAxisId="rhr" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="cont" orientation="right" domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
            <Line yAxisId="rhr"  type="monotone" dataKey="rhr"         name="Resting HR (bpm)" stroke="var(--negative)" strokeWidth={2} dot={false} connectNulls />
            <Line yAxisId="cont" type="monotone" dataKey="continuity"  name="Continuity %"     stroke="var(--positive)" strokeWidth={2} dot={false} connectNulls strokeDasharray="4 2" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Nightly detail table */}
      {records.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: 'var(--space-5) var(--space-6)', borderBottom: '1px solid var(--bg-border)' }}>
            <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>Nightly Detail</p>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, fontSize: 10 }}>
                  {['Date', 'Quality', 'Hours', 'Deep %', 'REM %', 'HR Dip', 'RHR', 'Cycles', 'Continuity'].map(h => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...records].reverse().map((s: any) => (
                  <tr key={s.date} style={{ borderTop: '1px solid var(--bg-border)' }}>
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>{s.date}</td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: sleepQualityColor(s.sleep_quality_composite) }}>
                      {s.sleep_quality_composite?.toFixed(0) ?? '—'}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)' }}>
                      {s.total_hours?.toFixed(1) ?? '—'}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', color: deepPctColor(s.deep_pct) }}>
                      {s.deep_pct?.toFixed(0) ?? '—'}%
                      {s.deep_sleep_deficit && <span style={{ color: 'var(--negative)', marginLeft: 4 }}>⚠️</span>}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', color: 'var(--info)' }}>
                      {s.rem_pct?.toFixed(0) ?? '—'}%
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', color: hrDipColor(s.nocturnal_hr_dip) }}>
                      {s.nocturnal_hr_dip?.toFixed(0) ?? '—'}%
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)' }}>
                      {s.resting_hr ?? '—'}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)' }}>
                      {s.sleep_cycles ?? '—'}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)' }}>
                      {s.continuity?.toFixed(1) ?? '—'}/5
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, unit, color, note }: any) {
  return (
    <div className="card-sm">
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-mono)', color: color ?? 'var(--text-primary)' }}>{value}</span>
        {unit && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{unit}</span>}
      </div>
      {note && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{note}</div>}
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
