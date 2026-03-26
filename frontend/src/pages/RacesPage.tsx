import { useState } from 'react'
import { useRaces, useCreateRace, useUpdateRace, useDeleteRace } from '@/hooks/useData'
import { format, parseISO, differenceInDays } from 'date-fns'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Race {
  id: number
  name: string
  race_date: string
  race_type: string
  priority: string
  target_finish_time?: string
  actual_finish_time?: string
  notes?: string
  completed: boolean
  override_base_tss?: number
  override_build_tss?: number
  override_peak_tss?: number
  plan?: any
}

const RACE_TYPES = [
  { value: 'marathon',      label: 'Marathon' },
  { value: 'half_marathon', label: 'Half Marathon' },
  { value: '10k',           label: '10K' },
  { value: '5k',            label: '5K' },
  { value: 'cycling',       label: 'Cycling' },
  { value: 'other',         label: 'Other' },
]

const PRIORITIES = [
  { value: 'A',    label: 'A — Season focus',     color: '#e8ff47' },
  { value: 'B',    label: 'B — Performance check', color: '#60a5fa' },
  { value: 'C',    label: 'C — Training race',     color: '#94a3b8' },
  { value: 'test', label: 'Test / Time trial',     color: '#a78bfa' },
]

// ─── Colour helpers ───────────────────────────────────────────────────────────
function priorityColor(p: string) {
  return PRIORITIES.find(x => x.value === p)?.color ?? '#94a3b8'
}

function phaseColor(phase: string) {
  const map: Record<string, string> = {
    base: '#60a5fa', build: '#a78bfa', peak: '#fb923c',
    taper: '#4ade80', race: '#e8ff47', recovery: '#94a3b8', off: '#475569',
  }
  return map[phase] ?? '#94a3b8'
}

function ackrStatusColor(achievable: boolean | undefined) {
  if (achievable === undefined) return 'var(--text-muted)'
  return achievable ? 'var(--positive)' : 'var(--warning)'
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function RacesPage() {
  const { data: races = [], isLoading } = useRaces()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Race | null>(null)

  const today = new Date()
  const upcoming = races.filter((r: Race) => !r.completed && new Date(r.race_date) >= today)
  const past     = races.filter((r: Race) =>  r.completed || new Date(r.race_date) <  today)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>Race Calendar</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
            {upcoming.length} upcoming · {past.length} completed
          </p>
        </div>
        <button onClick={() => { setEditing(null); setShowForm(true) }} style={primaryBtn}>
          + Add Race
        </button>
      </div>

      {/* Form modal */}
      {showForm && (
        <RaceForm
          initial={editing}
          onClose={() => { setShowForm(false); setEditing(null) }}
        />
      )}

      {isLoading && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>}

      {/* Upcoming races */}
      {upcoming.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {upcoming.map((r: Race) => (
            <RaceCard
              key={r.id} race={r}
              onEdit={() => { setEditing(r); setShowForm(true) }}
            />
          ))}
        </div>
      )}

      {upcoming.length === 0 && !isLoading && (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)',
          color: 'var(--text-muted)', fontSize: 14 }}>
          No races planned yet.<br />
          <span style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
            Add your first race to get phase tracking, CTL projections and TSS targets.
          </span>
        </div>
      )}

      {/* Past races */}
      {past.length > 0 && (
        <>
          <h2 style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)',
            textTransform: 'uppercase', letterSpacing: 1, marginBottom: 0 }}>
            Completed
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {[...past].reverse().map((r: Race) => (
              <RaceCardCompact
                key={r.id} race={r}
                onEdit={() => { setEditing(r); setShowForm(true) }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ─── Race Card (upcoming) ─────────────────────────────────────────────────────
function RaceCard({ race, onEdit }: { race: Race; onEdit: () => void }) {
  const plan       = race.plan
  const daysOut    = differenceInDays(parseISO(race.race_date), new Date())
  const phase      = plan?.phase ?? 'base'
  const milestones = plan?.milestones ?? []
  const [showDetail, setShowDetail] = useState(false)

  return (
    <div className="card" style={{ borderColor: priorityColor(race.priority) + '60' }}>

      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {/* Priority badge */}
          <div style={{
            width: 28, height: 28, borderRadius: 6, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            background: priorityColor(race.priority) + '20',
            border: `1px solid ${priorityColor(race.priority)}40`,
            fontSize: 13, fontWeight: 700, color: priorityColor(race.priority),
          }}>
            {race.priority}
          </div>
          <div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>{race.name}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              {format(parseISO(race.race_date), 'EEEE, MMMM d, yyyy')} ·{' '}
              {RACE_TYPES.find(t => t.value === race.race_type)?.label ?? race.race_type}
              {race.target_finish_time && ` · Target: ${race.target_finish_time}`}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {/* Days out */}
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-mono)',
              color: daysOut <= 14 ? 'var(--accent)' : 'var(--text-primary)' }}>
              {daysOut}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              days
            </div>
          </div>
          <button onClick={onEdit} style={ghostBtn}>Edit</button>
          <button onClick={() => setShowDetail(x => !x)} style={ghostBtn}>
            {showDetail ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* Phase bar */}
      <div style={{ marginTop: 'var(--space-5)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: phaseColor(phase),
              boxShadow: `0 0 6px ${phaseColor(phase)}`,
            }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: phaseColor(phase) }}>
              {plan?.phase_label ?? '—'} Phase
            </span>
            {plan?.weeks_in_phase != null && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                · week {Math.ceil(plan.weeks_in_phase)}
              </span>
            )}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {plan?.weeks_out?.toFixed(1)} weeks out
          </span>
        </div>

        {/* Phase timeline strip */}
        <PhaseTimeline plan={plan} raceDate={race.race_date} />
      </div>

      {/* Key metrics row */}
      {plan && (
        <div style={{ marginTop: 'var(--space-4)', display: 'flex', gap: 'var(--space-6)',
          flexWrap: 'wrap' }}>
          <PlanMetric label="Current CTL"    value={plan.current_ctl?.toFixed(0) ?? '—'} />
          <PlanMetric label="Target CTL"     value={plan.target_ctl ?? '—'} />
          <PlanMetric label="Projected CTL"  value={plan.projected_ctl_race?.toFixed(0) ?? '—'}
            color={ackrStatusColor(plan.achievable)} />
          <PlanMetric label="Proj. race TSB" value={plan.projected_tsb_race != null
            ? `${plan.projected_tsb_race > 0 ? '+' : ''}${plan.projected_tsb_race?.toFixed(0)}` : '—'}
            color={plan.projected_tsb_race >= plan.tsb_target - 5 ? 'var(--positive)' : 'var(--warning)'} />
          <PlanMetric label="Phase TSS/week" value={plan.current_phase_tss ?? '—'}
            color="var(--accent)" />
        </div>
      )}

      {/* Achievability */}
      {plan && (
        <div style={{
          marginTop: 'var(--space-3)', fontSize: 12,
          color: ackrStatusColor(plan.achievable),
          background: (plan.achievable ? 'rgba(74,222,128,' : 'rgba(251,191,36,') + '0.08)',
          padding: '5px 10px', borderRadius: 4,
          display: 'inline-block',
        }}>
          {plan.achievable ? '✓' : '⚠️'} {plan.gap_label}
        </div>
      )}

      {/* TSB warning */}
      {plan?.tsb_warning && (
        <div style={{
          marginTop: 8, fontSize: 12, color: 'var(--warning)',
          background: 'rgba(251,191,36,0.08)', padding: '5px 10px', borderRadius: 4,
        }}>
          ⚠️ {plan.tsb_warning}
        </div>
      )}

      {/* Expanded detail */}
      {showDetail && plan && (
        <div style={{ marginTop: 'var(--space-5)', borderTop: '1px solid var(--bg-border)',
          paddingTop: 'var(--space-5)', display: 'flex', flexDirection: 'column',
          gap: 'var(--space-5)' }}>

          <>
          {/* TSS targets per phase */}
          <div>
            <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
              letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
              Weekly TSS Targets
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
              {Object.entries(plan.weekly_targets ?? {}).map(([ph, tss]: any) => (
                <div key={ph} style={{
                  padding: '8px 14px', borderRadius: 'var(--radius-sm)',
                  background: phaseColor(ph) + '15',
                  border: `1px solid ${phaseColor(ph)}40`,
                  textAlign: 'center',
                  outline: ph === phase ? `2px solid ${phaseColor(ph)}` : 'none',
                }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)',
                    textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {ph} {ph === phase && '●'}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700,
                    fontFamily: 'var(--font-mono)', color: phaseColor(ph) }}>
                    {tss}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>TSS/week</div>
                </div>
              ))}
            </div>
          </div>

          {/* Milestones */}
          {milestones.length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
                letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
                Key Milestones
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {milestones.map((m: any, i: number) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    opacity: m.past ? 0.45 : 1,
                  }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                      background: m.past ? 'var(--text-muted)' : 'var(--accent)',
                    }} />
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: 13, fontWeight: m.past ? 400 : 500 }}>
                        {m.label}
                      </span>
                      {m.note && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                          {m.note}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                      {m.past ? 'done' : `${m.days_out}d`} · {format(parseISO(m.date), 'MMM d')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Nutrition guidance */}
          {plan.nutrition_guidance && (
            <div style={{
              padding: 'var(--space-4)', background: 'var(--bg-base)',
              borderRadius: 'var(--radius-sm)', borderLeft: `3px solid ${phaseColor(phase)}`,
            }}>
              <div style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
                letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 4 }}>
                🥗 Nutrition — {plan.phase_label} phase
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {plan.nutrition_guidance}
              </div>
            </div>
          )}
</>
        </div>
      )}
    </div>
  )
}

// ─── Phase timeline strip ─────────────────────────────────────────────────────
function PhaseTimeline({ plan, raceDate }: { plan: any; raceDate: string }) {
  if (!plan) return null
  const phases = [
    { key: 'base',  label: 'Base',  start: null,              end: plan.build_start },
    { key: 'build', label: 'Build', start: plan.build_start,  end: plan.peak_start  },
    { key: 'peak',  label: 'Peak',  start: plan.peak_start,   end: plan.taper_start },
    { key: 'taper', label: 'Taper', start: plan.taper_start,  end: raceDate         },
  ]

  return (
    <div style={{ display: 'flex', gap: 2, height: 24, borderRadius: 6, overflow: 'hidden' }}>
      {phases.map(p => (
        <div key={p.key} style={{
          flex: p.key === 'base' ? 3 : p.key === 'build' ? 3 : p.key === 'peak' ? 2 : 1,
          background: phaseColor(p.key) + (plan.phase === p.key ? 'cc' : '30'),
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, fontWeight: 600,
          color: plan.phase === p.key ? '#000' : phaseColor(p.key),
          letterSpacing: 0.5, textTransform: 'uppercase',
          border: plan.phase === p.key ? `2px solid ${phaseColor(p.key)}` : 'none',
          transition: 'all 0.2s',
        }}>
          {p.label}
        </div>
      ))}
      <div style={{
        width: 24, background: '#e8ff47cc',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, flexShrink: 0,
      }}>
        🏁
      </div>
    </div>
  )
}

// ─── Past race card (compact) ─────────────────────────────────────────────────
function RaceCardCompact({ race, onEdit }: { race: Race; onEdit: () => void }) {
  return (
    <div className="card-sm" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
      opacity: 0.75 }}>
      <div style={{
        width: 24, height: 24, borderRadius: 4, display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: priorityColor(race.priority) + '20',
        fontSize: 11, fontWeight: 700, color: priorityColor(race.priority), flexShrink: 0,
      }}>
        {race.priority}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 500 }}>{race.name}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {format(parseISO(race.race_date), 'MMM d, yyyy')} ·{' '}
          {RACE_TYPES.find(t => t.value === race.race_type)?.label}
        </div>
      </div>
      {race.actual_finish_time && (
        <div style={{ fontSize: 14, fontFamily: 'var(--font-mono)', fontWeight: 600,
          color: 'var(--positive)' }}>
          {race.actual_finish_time}
        </div>
      )}
      <button onClick={onEdit} style={ghostBtn}>Edit</button>
    </div>
  )
}

// ─── Race Form (create / edit) ────────────────────────────────────────────────
function RaceForm({ initial, onClose }: { initial: Race | null; onClose: () => void }) {
  const createMut = useCreateRace()
  const updateMut = useUpdateRace()
  const deleteMut = useDeleteRace()

  const [form, setForm] = useState({
    name:                initial?.name ?? '',
    race_date:           initial?.race_date ?? '',
    race_type:           initial?.race_type ?? 'half_marathon',
    priority:            initial?.priority ?? 'A',
    target_finish_time:  initial?.target_finish_time ?? '',
    actual_finish_time:  initial?.actual_finish_time ?? '',
    notes:               initial?.notes ?? '',
    completed:           initial?.completed ?? false,
    override_base_tss:   initial?.override_base_tss?.toString() ?? '',
    override_build_tss:  initial?.override_build_tss?.toString() ?? '',
    override_peak_tss:   initial?.override_peak_tss?.toString() ?? '',
  })

  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit() {
    const payload = {
      ...form,
      override_base_tss:  form.override_base_tss  ? parseInt(form.override_base_tss)  : null,
      override_build_tss: form.override_build_tss ? parseInt(form.override_build_tss) : null,
      override_peak_tss:  form.override_peak_tss  ? parseInt(form.override_peak_tss)  : null,
      target_finish_time: form.target_finish_time || null,
      actual_finish_time: form.actual_finish_time || null,
      notes:              form.notes || null,
    }
    if (initial) {
      await updateMut.mutateAsync({ id: initial.id, data: payload })
    } else {
      await createMut.mutateAsync(payload)
    }
    onClose()
  }

  async function handleDelete() {
    if (!initial || !confirm(`Delete "${initial.name}"?`)) return
    await deleteMut.mutateAsync(initial.id)
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 100, padding: 'var(--space-6)',
    }}>
      <div style={{
        background: 'var(--bg-surface)', borderRadius: 'var(--radius-md)',
        border: '1px solid var(--bg-border)', width: '100%', maxWidth: 560,
        padding: 'var(--space-8)', display: 'flex', flexDirection: 'column',
        gap: 'var(--space-5)', maxHeight: '90vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>
          {initial ? 'Edit Race' : 'Add Race'}
        </h2>

        <Field label="Race Name">
          <input value={form.name} onChange={e => set('name', e.target.value)}
            placeholder="e.g. Bucharest Half Marathon" style={inputStyle} />
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
          <Field label="Date">
            <input type="date" value={form.race_date} onChange={e => set('race_date', e.target.value)}
              style={inputStyle} />
          </Field>
          <Field label="Type">
            <select value={form.race_type} onChange={e => set('race_type', e.target.value)}
              style={inputStyle}>
              {RACE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>
        </div>

        <Field label="Priority">
          <div style={{ display: 'flex', gap: 8 }}>
            {PRIORITIES.map(p => (
              <button key={p.value} onClick={() => set('priority', p.value)} style={{
                flex: 1, padding: '8px 4px', borderRadius: 'var(--radius-sm)',
                border: `1px solid ${form.priority === p.value ? p.color : 'var(--bg-border)'}`,
                background: form.priority === p.value ? p.color + '20' : 'var(--bg-elevated)',
                color: form.priority === p.value ? p.color : 'var(--text-secondary)',
                fontSize: 12, fontWeight: form.priority === p.value ? 700 : 400,
                cursor: 'pointer',
              }}>
                {p.value}
              </button>
            ))}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            {PRIORITIES.find(p => p.value === form.priority)?.label}
          </div>
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
          <Field label="Target time (optional)">
            <input value={form.target_finish_time}
              onChange={e => set('target_finish_time', e.target.value)}
              placeholder="1:45:00" style={inputStyle} />
          </Field>
          {initial && (
            <Field label="Actual time">
              <input value={form.actual_finish_time}
                onChange={e => set('actual_finish_time', e.target.value)}
                placeholder="1:43:22" style={inputStyle} />
            </Field>
          )}
        </div>

        {/* TSS overrides */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)',
            marginBottom: 8 }}>
            TSS Targets Override <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>
              (leave blank to use computed defaults)
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-3)' }}>
            <Field label="Base TSS/week">
              <input type="number" value={form.override_base_tss}
                onChange={e => set('override_base_tss', e.target.value)}
                placeholder="auto" style={inputStyle} />
            </Field>
            <Field label="Build TSS/week">
              <input type="number" value={form.override_build_tss}
                onChange={e => set('override_build_tss', e.target.value)}
                placeholder="auto" style={inputStyle} />
            </Field>
            <Field label="Peak TSS/week">
              <input type="number" value={form.override_peak_tss}
                onChange={e => set('override_peak_tss', e.target.value)}
                placeholder="auto" style={inputStyle} />
            </Field>
          </div>
        </div>

        <Field label="Notes (optional)">
          <textarea value={form.notes} onChange={e => set('notes', e.target.value)}
            rows={2} placeholder="Course details, travel notes…" style={{ ...inputStyle, resize: 'vertical' }} />
        </Field>

        {initial && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input type="checkbox" checked={form.completed}
              onChange={e => set('completed', e.target.checked)} />
            Mark as completed
          </label>
        )}

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'space-between',
          marginTop: 'var(--space-2)' }}>
          <div>
            {initial && (
              <button onClick={handleDelete} style={dangerBtn}>Delete</button>
            )}
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <button onClick={onClose} style={ghostBtn}>Cancel</button>
            <button onClick={handleSubmit} style={primaryBtn}
              disabled={!form.name || !form.race_date}>
              {initial ? 'Save' : 'Add Race'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Small helpers ────────────────────────────────────────────────────────────
function PlanMetric({ label, value, color }: any) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, fontFamily: 'var(--font-mono)',
        color: color ?? 'var(--text-primary)', marginTop: 1 }}>
        {value}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)',
        textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </label>
      {children}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
  borderRadius: 'var(--radius-sm)', padding: '8px 10px',
  fontSize: 13, color: 'var(--text-primary)', width: '100%',
  outline: 'none', boxSizing: 'border-box',
}

const primaryBtn: React.CSSProperties = {
  padding: '8px 18px', background: 'var(--accent)', border: 'none',
  borderRadius: 'var(--radius-sm)', fontSize: 13, fontWeight: 600,
  color: '#000', cursor: 'pointer',
}

const ghostBtn: React.CSSProperties = {
  padding: '6px 12px', background: 'var(--bg-elevated)',
  border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)',
  fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
}

const dangerBtn: React.CSSProperties = {
  padding: '6px 12px', background: 'rgba(248,113,113,0.10)',
  border: '1px solid rgba(248,113,113,0.30)', borderRadius: 'var(--radius-sm)',
  fontSize: 12, color: 'var(--negative)', cursor: 'pointer',
}

