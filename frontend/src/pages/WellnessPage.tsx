import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, subDays, parseISO } from 'date-fns'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { api } from '@/utils/api'

// ─── API ──────────────────────────────────────────────────────────────────────
const wellnessApi = {
  list:        (params: any)   => api.get('/api/v1/wellness/', { params }),
  today:       ()              => api.get('/api/v1/wellness/today'),
  log:         (data: object)  => api.post('/api/v1/wellness/', data),
  delete:      (date: string)  => api.delete(`/api/v1/wellness/${date}`),
  correlation: (days: number)  => api.get('/api/v1/wellness/correlation', { params: { days } }),
}

// ─── Hooks ────────────────────────────────────────────────────────────────────
function useWellness(days: number) {
  const from = format(subDays(new Date(), days), 'yyyy-MM-dd')
  const to   = format(new Date(), 'yyyy-MM-dd')
  return useQuery({
    queryKey: ['wellness', days],
    queryFn:  () => wellnessApi.list({ from, to }).then(r => r.data),
  })
}

function useTodayWellness() {
  return useQuery({
    queryKey: ['wellness', 'today'],
    queryFn:  () => wellnessApi.today().then(r => r.data),
  })
}

function useLogWellness() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: object) => wellnessApi.log(data).then(r => r.data),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['wellness'] }),
  })
}

function useCorrelation(days: number) {
  return useQuery({
    queryKey: ['wellness-correlation', days],
    queryFn:  () => wellnessApi.correlation(days).then(r => r.data),
  })
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
const METRICS = [
  { key: 'energy',     label: 'Energy',    emoji: '⚡', desc: 'Overall energy level' },
  { key: 'mood',       label: 'Mood',      emoji: '😊', desc: 'Mood & motivation' },
  { key: 'soreness',   label: 'Soreness',  emoji: '💪', desc: 'Muscle soreness (5 = no soreness)' },
  { key: 'sleep_feel', label: 'Sleep',     emoji: '🌙', desc: 'How rested you feel' },
  { key: 'stress',     label: 'Stress',    emoji: '🧠', desc: 'Life stress (5 = no stress)' },
]

const SCORE_LABELS = ['', 'Very poor', 'Poor', 'Normal', 'Good', 'Excellent']

function scoreColor(score: number | null | undefined): string {
  if (score == null) return 'var(--text-muted)'
  if (score >= 80) return 'var(--positive)'
  if (score >= 60) return '#a3e635'
  if (score >= 40) return 'var(--warning)'
  return 'var(--negative)'
}

function metricColor(val: number | null | undefined): string {
  if (val == null) return 'var(--text-muted)'
  if (val >= 4) return 'var(--positive)'
  if (val >= 3) return 'var(--warning)'
  return 'var(--negative)'
}

// ─── Slider component ────────────────────────────────────────────────────────
function MetricSlider({
  metric, value, onChange,
}: {
  metric: typeof METRICS[0]
  value: number | null
  onChange: (v: number) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 18 }}>{metric.emoji}</span>
          <div>
            <span style={{ fontSize: 13, fontWeight: 500 }}>{metric.label}</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>
              {metric.desc}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 11, color: metricColor(value),
            fontWeight: 500, minWidth: 60, textAlign: 'right',
          }}>
            {value ? SCORE_LABELS[value] : 'Not set'}
          </span>
          <span style={{
            fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)',
            color: metricColor(value), minWidth: 20, textAlign: 'center',
          }}>
            {value ?? '—'}
          </span>
        </div>
      </div>

      {/* 5-button selector */}
      <div style={{ display: 'flex', gap: 4 }}>
        {[1, 2, 3, 4, 5].map(n => (
          <button
            key={n}
            onClick={() => onChange(n)}
            style={{
              flex: 1, height: 36, borderRadius: 'var(--radius-sm)',
              border: '1px solid',
              borderColor: value === n ? metricColor(n) : 'var(--bg-border)',
              background: value === n ? metricColor(n) + '25' : 'var(--bg-elevated)',
              color: value === n ? metricColor(n) : 'var(--text-muted)',
              fontSize: 13, fontWeight: value === n ? 700 : 400,
              cursor: 'pointer', transition: 'all 0.1s',
            }}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Check-in form ────────────────────────────────────────────────────────────
function CheckInForm({ existing }: { existing: any }) {
  const today  = format(new Date(), 'yyyy-MM-dd')
  const logMut = useLogWellness()

  const [form, setForm] = useState({
    energy:     existing?.energy     ?? null,
    mood:       existing?.mood       ?? null,
    soreness:   existing?.soreness   ?? null,
    sleep_feel: existing?.sleep_feel ?? null,
    stress:     existing?.stress     ?? null,
    notes:      existing?.notes      ?? '',
  })

  const composite = (() => {
    const vals = [form.energy, form.mood, form.soreness, form.sleep_feel, form.stress]
      .filter(v => v != null) as number[]
    if (!vals.length) return null
    return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length * 20)
  })()

  const allSet = [form.energy, form.mood, form.soreness, form.sleep_feel, form.stress]
    .every(v => v != null)

  async function handleSubmit() {
    await logMut.mutateAsync({ log_date: today, ...form })
  }

  return (
    <div className="card" style={{
      borderColor: composite ? scoreColor(composite) + '60' : 'var(--bg-border)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', marginBottom: 'var(--space-5)' }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
            letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 4 }}>
            Today's Wellness Check-in
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {format(new Date(), 'EEEE, MMMM d')} · ~60 seconds
          </p>
        </div>
        {composite != null && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 36, fontWeight: 800,
              fontFamily: 'var(--font-mono)', color: scoreColor(composite), lineHeight: 1 }}>
              {composite}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>/ 100</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        {METRICS.map(m => (
          <MetricSlider
            key={m.key}
            metric={m}
            value={(form as any)[m.key]}
            onChange={v => setForm(f => ({ ...f, [m.key]: v }))}
          />
        ))}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 11, color: 'var(--text-muted)',
            textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Notes (optional)
          </label>
          <textarea
            value={form.notes}
            onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
            rows={2}
            placeholder="Feeling heavy legs from yesterday's run, stressful work week…"
            style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
              borderRadius: 'var(--radius-sm)', padding: '8px 10px',
              fontSize: 13, color: 'var(--text-primary)', resize: 'vertical',
              outline: 'none',
            }}
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={!allSet || logMut.isPending}
          style={{
            padding: '10px 20px',
            background: allSet ? 'var(--accent)' : 'var(--bg-elevated)',
            border: 'none', borderRadius: 'var(--radius-sm)',
            fontSize: 13, fontWeight: 600,
            color: allSet ? '#000' : 'var(--text-muted)',
            cursor: allSet ? 'pointer' : 'not-allowed',
            transition: 'all 0.15s',
          }}
        >
          {logMut.isPending
            ? 'Saving…'
            : existing
            ? '✓ Update Check-in'
            : '✓ Save Check-in'}
        </button>
        {!allSet && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: -8 }}>
            Rate all 5 metrics to save
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function WellnessPage() {
  const [days, setDays] = useState(30)
  const { data: todayEntry }           = useTodayWellness()
  const { data: history = [] }         = useWellness(days)
  const { data: correlation }          = useCorrelation(days)

  const sorted = [...history].sort((a: any, b: any) => a.date.localeCompare(b.date))

  // Chart data — composite trend
  const trendData = sorted.map((w: any) => ({
    date:      w.date.slice(5),
    composite: w.composite,
    energy:    w.energy ? w.energy * 20 : null,
    mood:      w.mood   ? w.mood   * 20 : null,
    soreness:  w.soreness ? w.soreness * 20 : null,
  }))

  // Correlation chart — prev day TSS vs today's composite
  const corrData = (correlation?.points ?? [])
    .filter((p: any) => p.composite != null && p.prev_day_tss != null)
    .map((p: any) => ({
      date:     p.date.slice(5),
      wellness: p.composite,
      tss:      p.prev_day_tss,
      atl:      p.atl,
    }))

  // Period averages
  const avgComposite = (() => {
    const vals = history.map((w: any) => w.composite).filter((v: any) => v != null)
    if (!vals.length) return null
    return Math.round(vals.reduce((a: number, b: number) => a + b, 0) / vals.length)
  })()

  const avgByMetric = METRICS.map(m => {
    const vals = history.map((w: any) => (w as any)[m.key]).filter((v: any) => v != null) as number[]
    const avg  = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
    return { ...m, avg: avg ? Math.round(avg * 10) / 10 : null }
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>Wellness</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
            Daily check-in · predicts overtraining before your metrics do
          </p>
        </div>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* Check-in form — always at top */}
      <CheckInForm existing={todayEntry} />

      {/* Period summary stats */}
      {history.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)',
          gap: 'var(--space-3)' }}>
          {avgByMetric.map(m => (
            <div key={m.key} className="card-sm" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, marginBottom: 4 }}>{m.emoji}</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)',
                color: metricColor(m.avg) }}>
                {m.avg?.toFixed(1) ?? '—'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)',
                textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 2 }}>
                {m.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Composite trend chart */}
      {trendData.length > 1 && (
        <div className="card">
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)',
            marginBottom: 4 }}>
            Wellness Composite Score — {days} day trend
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
            Overall score (0-100) · avg: {avgComposite ?? '—'}
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false}
                interval={Math.floor(trendData.length / 7)} />
              <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={60} stroke="var(--text-muted)" strokeDasharray="3 3"
                label={{ value: 'Normal', fill: 'var(--text-muted)', fontSize: 9,
                  position: 'insideTopRight' }} />
              <Bar dataKey="composite" name="Composite" fill="var(--accent)"
                opacity={0.8} maxBarSize={16} radius={[2, 2, 0, 0]} />
              <Line type="monotone" dataKey="mood" name="Mood ×20"
                stroke="var(--info)" strokeWidth={1.5} dot={false} connectNulls
                strokeDasharray="4 2" />
              <Line type="monotone" dataKey="energy" name="Energy ×20"
                stroke="var(--positive)" strokeWidth={1.5} dot={false} connectNulls
                strokeDasharray="4 2" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* TSS vs Wellness correlation */}
      {corrData.length > 5 && (
        <div className="card">
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)',
            marginBottom: 4 }}>
            Training Load vs Next-Day Wellness
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
            Yesterday's TSS paired with today's wellness score.
            Downward trend in wellness as load rises = approaching your personal threshold.
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={corrData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false}
                interval={Math.floor(corrData.length / 7)} />
              <YAxis yAxisId="w" domain={[0, 100]}
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false} />
              <YAxis yAxisId="t" orientation="right"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
              <Bar yAxisId="t" dataKey="tss" name="TSS" fill="var(--accent)"
                opacity={0.4} maxBarSize={12} radius={[2, 2, 0, 0]} />
              <Line yAxisId="w" type="monotone" dataKey="wellness" name="Wellness"
                stroke="var(--positive)" strokeWidth={2} dot={false} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* History table */}
      {history.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: 'var(--space-5) var(--space-6)',
            borderBottom: '1px solid var(--bg-border)' }}>
            <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>
              History
            </p>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', textTransform: 'uppercase',
                  letterSpacing: 0.5, fontSize: 10 }}>
                  {['Date', 'Score', '⚡', '😊', '💪', '🌙', '🧠', 'Notes'].map(h => (
                    <th key={h} style={{ padding: '10px 14px', textAlign: 'left',
                      fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().map((w: any) => (
                  <tr key={w.date} style={{ borderTop: '1px solid var(--bg-border)' }}>
                    <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>
                      {w.date}
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)',
                      fontWeight: 700, color: scoreColor(w.composite) }}>
                      {w.composite ?? '—'}
                    </td>
                    {['energy', 'mood', 'soreness', 'sleep_feel', 'stress'].map(k => (
                      <td key={k} style={{ padding: '10px 14px',
                        fontFamily: 'var(--font-mono)', color: metricColor((w as any)[k]) }}>
                        {(w as any)[k] ?? '—'}
                      </td>
                    ))}
                    <td style={{ padding: '10px 14px', color: 'var(--text-muted)',
                      fontSize: 11, maxWidth: 200, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {w.notes ?? ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {history.length === 0 && !todayEntry && (
        <div style={{ textAlign: 'center', padding: 'var(--space-10)',
          color: 'var(--text-muted)', fontSize: 13 }}>
          Complete your first check-in above to start tracking wellness trends.
          <br />
          <span style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
            After 2-3 weeks of data the correlation chart will show your personal
            training load tolerance threshold.
          </span>
        </div>
      )}
    </div>
  )
}

function RangePicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {[14, 30, 60].map(n => (
        <button key={n} onClick={() => onChange(n)} style={{
          padding: '6px 12px', fontSize: 12, borderRadius: 'var(--radius-sm)',
          border: '1px solid',
          borderColor: value === n ? 'var(--accent)' : 'var(--bg-border)',
          background: value === n ? 'var(--accent-muted)' : 'var(--bg-elevated)',
          color: value === n ? 'var(--accent)' : 'var(--text-secondary)',
          transition: 'all 0.15s',
        }}>{n}d</button>
      ))}
    </div>
  )
}
