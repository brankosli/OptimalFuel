import { useState } from 'react'
import { useActivities, usePMC, useNextRace, useRaceTemplate } from '@/hooks/useData'
import { formatDuration, formatDistance, formatPace, sportIcon, formatCalories,
         acwrColor, acwrLabel, acwrBg, monotonyColor } from '@/utils/format'
import { format, parseISO } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

// ─── Sport emoji ──────────────────────────────────────────────────────────────
function sessionEmoji(type: string) {
  const map: Record<string, string> = {
    run: '🏃', ride: '🚴', strength: '🏋️', walk: '🚶', rest: '😴', race: '🏁',
  }
  return map[type] ?? '🏅'
}

function phaseColor(phase: string) {
  const map: Record<string, string> = {
    base: '#60a5fa', build: '#a78bfa', peak: '#fb923c',
    taper: '#4ade80', race: '#e8ff47', recovery: '#94a3b8',
  }
  return map[phase] ?? '#60a5fa'
}

// ─── This Week's Plan section ─────────────────────────────────────────────────
function ThisWeeksPlan() {
  const { data: nextRace } = useNextRace()
  const { data: templateData, isLoading } = useRaceTemplate(nextRace?.id ?? null)
  const template = templateData?.template
  const plan     = templateData?.plan

  if (!nextRace) return (
    <div className="card" style={{ borderColor: 'var(--bg-border)' }}>
      <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
        letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
        This Week's Training Plan
      </p>
      <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
        Add a race in the 🏁 Races page to get a phase-specific training plan here.
      </p>
    </div>
  )

  if (isLoading) return (
    <div className="card">
      <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
        letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
        This Week's Training Plan
      </p>
      <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading…</p>
    </div>
  )

  if (!template) return null

  const color = plan?.phase_color ?? phaseColor(plan?.phase ?? 'base')

  return (
    <div className="card" style={{ borderColor: color + '50' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', marginBottom: 'var(--space-5)' }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
            letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 4 }}>
            This Week's Training Plan
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', background: color,
              boxShadow: `0 0 6px ${color}`,
            }} />
            <span style={{ fontSize: 15, fontWeight: 600, color }}>
              {plan?.phase_label} Phase
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              · {nextRace.name}
            </span>
            {plan?.weeks_out && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                · {plan.weeks_out} weeks out
              </span>
            )}
          </div>
        </div>

        {/* Phase stats */}
        <div style={{ display: 'flex', gap: 'var(--space-5)', flexShrink: 0 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)',
              textTransform: 'uppercase', letterSpacing: 0.5 }}>
              TSS target
            </div>
            <div style={{ fontSize: 16, fontWeight: 700,
              fontFamily: 'var(--font-mono)', color }}>
              {plan?.current_phase_tss ?? '—'}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)',
              textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Est. TSS
            </div>
            <div style={{ fontSize: 16, fontWeight: 700,
              fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              ~{template.estimated_tss}
            </div>
          </div>
        </div>
      </div>

      {/* Focus line */}
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6,
        marginBottom: 'var(--space-5)', paddingBottom: 'var(--space-5)',
        borderBottom: '1px solid var(--bg-border)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>Focus:</strong> {template.focus}
        <span style={{ color: 'var(--text-muted)', marginLeft: 12 }}>
          {template.intensity_split}
        </span>
      </p>

      {/* Day-by-day sessions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {template.days?.map((session: any, i: number) => (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '76px 26px 1fr auto',
            alignItems: 'center',
            gap: 'var(--space-3)',
            padding: '9px 12px',
            borderRadius: 'var(--radius-sm)',
            background: session.key
              ? (session.zone_color ?? color) + '12'
              : session.type === 'rest'
              ? 'transparent'
              : 'var(--bg-elevated)',
            border: session.key
              ? `1px solid ${session.zone_color ?? color}40`
              : '1px solid transparent',
          }}>
            {/* Day name */}
            <div style={{
              fontSize: 11,
              fontWeight: session.key ? 600 : 400,
              color: session.key ? 'var(--text-primary)' : 'var(--text-muted)',
            }}>
              {session.day}
            </div>

            {/* Emoji */}
            <div style={{ fontSize: 16, textAlign: 'center' }}>
              {sessionEmoji(session.type)}
            </div>

            {/* Session details */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  fontSize: 13,
                  fontWeight: session.key ? 600 : session.type === 'rest' ? 400 : 500,
                  color: session.type === 'rest'
                    ? 'var(--text-muted)'
                    : 'var(--text-primary)',
                }}>
                  {session.label}
                </span>
                {session.key && (
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: '1px 5px',
                    borderRadius: 3, textTransform: 'uppercase', letterSpacing: 0.5,
                    background: (session.zone_color ?? color) + '25',
                    color: session.zone_color ?? color,
                  }}>
                    Key
                  </span>
                )}
              </div>
              {session.type !== 'rest' && session.type !== 'race' && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1,
                  display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ color: session.zone_color ?? 'var(--text-muted)' }}>
                    {session.zone_label}
                  </span>
                  {session.hr_min && session.hr_max && (
                    <span style={{ color: '#fb7185' }}>
                      ❤️ {session.hr_min}–{session.hr_max} bpm
                    </span>
                  )}
                  {session.purpose && (
                    <span>· {session.purpose}</span>
                  )}
                </div>
              )}
            </div>

            {/* Duration */}
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              {session.duration_min > 0 ? (
                <span style={{ fontSize: 13, fontWeight: 600,
                  fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {session.duration_min}m
                </span>
              ) : session.type === 'race' ? (
                <span style={{ fontSize: 18 }}>🏁</span>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {/* Coach note */}
      <div style={{
        marginTop: 'var(--space-5)',
        padding: '10px 14px',
        background: 'rgba(232,255,71,0.05)',
        borderRadius: 'var(--radius-sm)',
        borderLeft: '3px solid var(--accent)',
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)',
          textTransform: 'uppercase', letterSpacing: 0.5, marginRight: 8 }}>
          💡
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          {template.weekly_note}
        </span>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function TrainingPage() {
  const [days, setDays] = useState(30)
  const { data: activities = [], isLoading } = useActivities(days)
  const { data: pmcData = [] } = usePMC(days)

  const latest = pmcData.length ? pmcData[pmcData.length - 1] as any : null
  const weeklyTSS = buildWeeklyTSS(activities)

  const acwrTrend = (pmcData as any[])
    .filter(d => d.acwr != null)
    .map(d => ({
      date: d.date.slice(5),
      acwr: d.acwr,
      fill: d.acwr > 1.5 ? '#ef4444' : d.acwr > 1.3 ? '#fb923c' : d.acwr >= 0.8 ? '#4ade80' : '#60a5fa',
    }))

  const visibleActivities = activities.filter((a: any) => a.source !== 'polar_dedup' && a.source !== 'strava_dedup')
  const dedupCount = activities.length - visibleActivities.length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Training</h1>
        <RangePicker value={days} onChange={setDays} />
      </div>

      {/* ── This Week's Plan ─────────────────────────── */}
      <ThisWeeksPlan />

      {/* ── Metric cards ─────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)' }}>

        <div className="card" style={{
          background: acwrBg(latest?.acwr),
          borderColor: acwrColor(latest?.acwr),
        }}>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1,
            color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
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

        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1,
            color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
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
            &gt;2.0 = overtraining risk (Foster 1998)
          </div>
        </div>

        <div className="card">
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1,
            color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
            Current Fitness (CTL)
          </p>
          <div style={{ fontSize: 36, fontWeight: 700, color: 'var(--positive)', lineHeight: 1 }}>
            {latest?.ctl?.toFixed(0) ?? '—'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Chronic Training Load
          </div>
          <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-4)' }}>
            <SmMetric label="ATL" value={latest?.atl?.toFixed(0) ?? '—'} color="var(--negative)" />
            <SmMetric label="TSB" value={latest?.tsb?.toFixed(0) ?? '—'}
              color={latest?.tsb == null ? 'var(--text-muted)'
                : latest.tsb >= 0 ? 'var(--positive)' : 'var(--warning)'} />
            <SmMetric label="Strain" value={latest?.training_strain?.toFixed(0) ?? '—'} />
          </div>
        </div>
      </div>

      {/* ── ACWR trend ───────────────────────────────── */}
      {acwrTrend.length > 0 && (
        <div className="card">
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>
            ACWR Trend — injury risk over time
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
            🟢 Safe (0.8-1.3) · 🟠 Caution (&gt;1.3) · 🔴 Danger (&gt;1.5) · 🔵 Detraining (&lt;0.8)
          </p>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={acwrTrend} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false}
                interval={Math.floor(acwrTrend.length / 7)} />
              <YAxis domain={[0, 2]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [v.toFixed(2), 'ACWR']} />
              <ReferenceLine y={1.3} stroke="#fb923c" strokeDasharray="3 3"
                label={{ value: '1.3', fill: '#fb923c', fontSize: 9, position: 'insideTopRight' }} />
              <ReferenceLine y={0.8} stroke="var(--info)" strokeDasharray="3 3"
                label={{ value: '0.8', fill: 'var(--info)', fontSize: 9, position: 'insideBottomRight' }} />
              <Bar dataKey="acwr" maxBarSize={10} radius={[2, 2, 0, 0]}>
                {acwrTrend.map((e: any, i: number) => <Cell key={i} fill={e.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Weekly TSS ───────────────────────────────── */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)',
          marginBottom: 'var(--space-5)' }}>
          Weekly Training Load (TSS)
        </p>
        {weeklyTSS.length === 0 ? (
          <div style={{ height: 150, display: 'flex', alignItems: 'center',
            justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No TSS data — set your LTHR in Settings
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={weeklyTSS} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
              <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: 'var(--accent-muted)' }} />
              <Bar dataKey="tss" name="TSS" fill="var(--accent)"
                radius={[3, 3, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Activity list ────────────────────────────── */}
      <div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
          {visibleActivities.length} activities
          {dedupCount > 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>
              ({dedupCount} duplicates hidden)
            </span>
          )}
        </p>
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
        ) : visibleActivities.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: 'var(--space-8)' }}>
            No activities found. Sync your data to get started.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {visibleActivities.map((a: any) => <ActivityCard key={a.id} activity={a} />)}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SmMetric({ label, value, color }: any) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-mono)',
        color: color ?? 'var(--text-primary)', marginTop: 1 }}>
        {value}
      </div>
    </div>
  )
}

function ActivityCard({ activity: a }: { activity: any }) {
  const isRun  = a.sport_type === 'run'
  const isRide = a.sport_type === 'ride'
  return (
    <div className="card-sm" style={{ display: 'grid',
      gridTemplateColumns: '40px 1fr auto', gap: 'var(--space-4)', alignItems: 'center' }}>
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
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3,
          display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
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
          <><div style={{ fontSize: 18, fontWeight: 700,
            fontFamily: 'var(--font-mono)' }}>{a.tss}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>TSS</div></>
        ) : a.calories ? (
          <><div style={{ fontSize: 14, fontWeight: 600,
            fontFamily: 'var(--font-mono)' }}>{Math.round(a.calories)}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>kcal</div></>
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
        }}>{n}d</button>
      ))}
    </div>
  )
}

function buildWeeklyTSS(activities: any[]) {
  const weeks: Record<string, number> = {}
  for (const a of activities) {
    if (!a.date || !a.tss || a.source === 'polar_dedup' || a.source === 'strava_dedup') continue
    const w = format(parseISO(a.date), "'W'w")
    weeks[w] = (weeks[w] ?? 0) + a.tss
  }
  return Object.entries(weeks).sort(([a], [b]) => a.localeCompare(b))
    .map(([week, tss]) => ({ week, tss: Math.round(tss) }))
}
