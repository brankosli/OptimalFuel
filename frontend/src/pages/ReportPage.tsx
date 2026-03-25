import { useState } from 'react'
import { useWeeklyReport } from '@/hooks/useData'
import { sportIcon } from '@/utils/format'

// ─── Colour helpers ───────────────────────────────────────────────────────────
function statusColor(status: string): string {
  switch (status) {
    case 'good':    return 'var(--positive)'
    case 'ok':      return 'var(--info)'
    case 'neutral': return 'var(--text-secondary)'
    case 'warning': return 'var(--warning)'
    case 'bad':
    case 'danger':  return 'var(--negative)'
    default:        return 'var(--text-muted)'
  }
}

function statusBg(status: string): string {
  switch (status) {
    case 'good':    return 'rgba(74,222,128,0.10)'
    case 'ok':      return 'rgba(96,165,250,0.10)'
    case 'neutral': return 'var(--bg-elevated)'
    case 'warning': return 'rgba(251,191,36,0.10)'
    case 'bad':
    case 'danger':  return 'rgba(248,113,113,0.10)'
    default:        return 'var(--bg-elevated)'
  }
}

function acwrColor(status: string) {
  switch (status) {
    case 'safe':    return 'var(--positive)'
    case 'caution': return 'var(--warning)'
    case 'danger':  return 'var(--negative)'
    case 'low':     return 'var(--info)'
    default:        return 'var(--text-muted)'
  }
}

function tsbColor(tsb: number | null | undefined) {
  if (tsb == null) return 'var(--text-muted)'
  if (tsb >= 10)  return 'var(--positive)'
  if (tsb >= -5)  return 'var(--warning)'
  return 'var(--negative)'
}

function sleepColor(q: number | null | undefined) {
  if (q == null) return 'var(--text-muted)'
  if (q >= 75) return 'var(--positive)'
  if (q >= 55) return 'var(--warning)'
  return 'var(--negative)'
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function ReportPage() {
  const [weekOffset, setWeekOffset] = useState(0)
  const { data: report, isLoading, error } = useWeeklyReport(weekOffset)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>Weekly Report</h1>
          {report && (
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
              {report.week_label}
            </p>
          )}
        </div>
        <WeekPicker value={weekOffset} onChange={setWeekOffset} />
      </div>

      {isLoading && (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Generating report…</div>
      )}

      {error && (
        <div style={{ color: 'var(--negative)', fontSize: 13 }}>
          Could not load report — trigger a sync first.
        </div>
      )}

      {report && !isLoading && (
        <>
          {/* ── Highlight badges ──────────────────────────── */}
          {report.highlights?.length > 0 && (
            <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
              {report.highlights.map((h: any, i: number) => (
                <div key={i} style={{
                  padding: '8px 14px', borderRadius: 'var(--radius-sm)',
                  background: statusBg(h.status),
                  border: `1px solid ${statusColor(h.status)}40`,
                  display: 'flex', flexDirection: 'column', gap: 2,
                }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)',
                    textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {h.label}
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700,
                    fontFamily: 'var(--font-mono)', color: statusColor(h.status) }}>
                    {h.value}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Top row: Load + Fitness + Risk ───────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)' }}>

            {/* Training Load */}
            <div className="card">
              <SectionLabel>Training Load</SectionLabel>
              <BigStat
                value={report.weekly_tss?.toFixed(0) ?? '—'}
                unit="TSS"
                sub={report.tss_change_pct != null
                  ? `${report.tss_arrow} ${report.tss_change_pct > 0 ? '+' : ''}${report.tss_change_pct?.toFixed(0)}% vs last week`
                  : undefined}
                subColor={Math.abs(report.tss_change_pct ?? 0) > 20
                  ? 'var(--warning)' : 'var(--text-muted)'}
              />
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-5)' }}>
                <SmStat label="Sessions" value={report.num_sessions} />
                <SmStat label="Hours"    value={report.total_hours?.toFixed(1)} />
                <SmStat label="Prev TSS" value={report.prev_tss?.toFixed(0) ?? '—'} />
              </div>
            </div>

            {/* Fitness */}
            <div className="card">
              <SectionLabel>Fitness (CTL)</SectionLabel>
              <BigStat
                value={report.ctl_end?.toFixed(0) ?? '—'}
                unit="CTL"
                sub={report.ctl_gain != null
                  ? `${report.ctl_gain > 0 ? '+' : ''}${report.ctl_gain} this week`
                  : undefined}
                subColor={report.ctl_gain != null && report.ctl_gain > 0
                  ? 'var(--positive)' : 'var(--text-muted)'}
              />
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-5)' }}>
                <SmStat label="ATL"    value={report.atl_end?.toFixed(0) ?? '—'} />
                <SmStat label="TSB"    value={report.tsb_end?.toFixed(0) ?? '—'}
                  color={tsbColor(report.tsb_end)} />
                <SmStat label="CTL start" value={report.ctl_start?.toFixed(0) ?? '—'} />
              </div>
            </div>

            {/* Injury Risk */}
            <div className="card" style={{ borderColor: acwrColor(report.acwr_status) + '60' }}>
              <SectionLabel>Injury Risk (ACWR)</SectionLabel>
              <BigStat
                value={report.acwr_max?.toFixed(2) ?? '—'}
                unit="peak"
                sub={report.acwr_status?.toUpperCase()}
                subColor={acwrColor(report.acwr_status)}
              />
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-5)' }}>
                <SmStat label="Avg ACWR"  value={report.acwr_avg?.toFixed(2) ?? '—'} />
                <SmStat label="Monotony"  value={report.training_monotony?.toFixed(2) ?? '—'}
                  color={report.training_monotony > 2 ? 'var(--warning)' : 'var(--positive)'} />
              </div>
            </div>
          </div>

          {/* ── Sport breakdown ───────────────────────────── */}
          {report.sport_breakdown && Object.keys(report.sport_breakdown).length > 0 && (
            <div className="card">
              <SectionLabel>Sessions by Sport</SectionLabel>
              <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', marginTop: 'var(--space-3)' }}>
                {Object.entries(report.sport_breakdown).map(([sport, count]: any) => (
                  <div key={sport} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '8px 14px', borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--bg-border)',
                  }}>
                    <span style={{ fontSize: 20 }}>{sportIcon(sport)}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500, textTransform: 'capitalize' }}>{sport}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {count} session{count !== 1 ? 's' : ''}
                        {report.sport_tss?.[sport] > 0 && ` · ${report.sport_tss[sport].toFixed(0)} TSS`}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Sleep row ─────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
            <div className="card">
              <SectionLabel>Sleep Quality</SectionLabel>
              <BigStat
                value={report.avg_sleep_quality?.toFixed(0) ?? '—'}
                unit="/ 100"
                sub={`${report.avg_sleep_hours?.toFixed(1) ?? '—'} hrs avg`}
              />
              <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-5)' }}>
                <SmStat label="Deficit nights" value={report.deficit_nights}
                  color={report.deficit_nights > 2 ? 'var(--negative)' : report.deficit_nights > 0 ? 'var(--warning)' : 'var(--positive)'} />
                <SmStat label="Avg HR dip" value={report.avg_hr_dip != null ? `${report.avg_hr_dip?.toFixed(0)}%` : '—'}
                  color={report.avg_hr_dip >= 10 ? 'var(--positive)' : report.avg_hr_dip >= 8 ? 'var(--warning)' : 'var(--negative)'} />
                {report.sleep_debt_minutes != null && (
                  <SmStat label="Sleep debt"
                    value={`${Math.floor(report.sleep_debt_minutes / 60)}h ${report.sleep_debt_minutes % 60}m`}
                    color={report.sleep_debt_minutes > 120 ? 'var(--negative)' : 'var(--warning)'} />
                )}
              </div>
            </div>

            {/* Next week guidance */}
            <div className="card" style={{ background: 'rgba(232,255,71,0.04)', borderColor: 'var(--accent)40' }}>
              <SectionLabel>Next Week Target</SectionLabel>
              {report.next_tss_target && (
                <BigStat
                  value={report.next_tss_target}
                  unit="TSS target"
                  subColor="var(--accent)"
                />
              )}
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7,
                marginTop: 'var(--space-3)' }}>
                {report.next_week_guidance}
              </p>
            </div>
          </div>

          {/* ── Narrative sections ────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <NarrativeCard title="📊 Training Load" text={report.load_narrative} />
            <NarrativeCard title="⚡ Injury Risk" text={report.acwr_narrative}
              accent={report.acwr_status === 'danger' ? 'var(--negative)'
                : report.acwr_status === 'caution' ? 'var(--warning)' : undefined} />
            <NarrativeCard title="🌙 Sleep & Recovery" text={report.sleep_narrative} />
            <NarrativeCard title="🔋 Going Into Next Week" text={report.recovery_narrative} />
          </div>
        </>
      )}
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
      letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
      {children}
    </p>
  )
}

function BigStat({ value, unit, sub, subColor }: any) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span style={{ fontSize: 36, fontWeight: 700, fontFamily: 'var(--font-mono)',
          color: 'var(--text-primary)', lineHeight: 1 }}>
          {value}
        </span>
        {unit && <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{unit}</span>}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: subColor ?? 'var(--text-muted)', marginTop: 3 }}>
          {sub}
        </div>
      )}
    </div>
  )
}

function SmStat({ label, value, color }: any) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase',
        letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, fontFamily: 'var(--font-mono)',
        color: color ?? 'var(--text-primary)', marginTop: 1 }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

function NarrativeCard({ title, text, accent }: any) {
  return (
    <div className="card" style={accent ? { borderColor: accent + '60' } : {}}>
      <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 'var(--space-3)',
        color: accent ?? 'var(--text-primary)' }}>
        {title}
      </p>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8, margin: 0 }}>
        {text}
      </p>
    </div>
  )
}

function WeekPicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
      <button onClick={() => onChange(value - 1)} style={navBtn}>‹ Prev</button>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)', minWidth: 80, textAlign: 'center' }}>
        {value === 0 ? 'This week' : value === -1 ? 'Last week' : `${Math.abs(value)}w ago`}
      </span>
      <button onClick={() => onChange(value + 1)} disabled={value >= 0}
        style={{ ...navBtn, opacity: value >= 0 ? 0.3 : 1 }}>
        Next ›
      </button>
    </div>
  )
}

const navBtn: React.CSSProperties = {
  padding: '6px 12px', fontSize: 12,
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--bg-border)',
  background: 'var(--bg-elevated)',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
}
