import { useState, useEffect } from 'react'
import { useProfile, useUpdateProfile, useAuthStatus } from '@/hooks/useData'

export default function SettingsPage() {
  const { data: profile } = useProfile()
  const { data: auth } = useAuthStatus()
  const updateProfile = useUpdateProfile()

  const [form, setForm] = useState({
    weight_kg: '', height_cm: '', age: '', sex: 'male',
    ftp_watts: '', lthr_bpm: '', vo2max: '',
    protein_target_per_kg: '1.8', dietary_preference: 'omnivore',
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (profile?.configured) {
      setForm({
        weight_kg: profile.weight_kg?.toString() ?? '',
        height_cm: profile.height_cm?.toString() ?? '',
        age: profile.age?.toString() ?? '',
        sex: profile.sex ?? 'male',
        ftp_watts: profile.ftp_watts?.toString() ?? '',
        lthr_bpm: profile.lthr_bpm?.toString() ?? '',
        vo2max: profile.vo2max?.toString() ?? '',
        protein_target_per_kg: profile.protein_target_per_kg?.toString() ?? '1.8',
        dietary_preference: profile.dietary_preference ?? 'omnivore',
      })
    }
  }, [profile])

  const handleSave = async () => {
    await updateProfile.mutateAsync({
      weight_kg: form.weight_kg ? +form.weight_kg : null,
      height_cm: form.height_cm ? +form.height_cm : null,
      age: form.age ? +form.age : null,
      sex: form.sex,
      ftp_watts: form.ftp_watts ? +form.ftp_watts : null,
      lthr_bpm: form.lthr_bpm ? +form.lthr_bpm : null,
      vo2max: form.vo2max ? +form.vo2max : null,
      protein_target_per_kg: +form.protein_target_per_kg,
      dietary_preference: form.dietary_preference,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)', maxWidth: 600 }}>
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Settings</h1>

      {/* ── Connections ──────────────────────────────────── */}
      <Section title="Connections">
        <ConnectionRow
          label="Polar Flow"
          connected={auth?.polar?.connected}
          connectUrl="/api/v1/auth/polar"
          description="Sleep, HRV, Nightly Recharge, training load"
        />
        <ConnectionRow
          label="Strava"
          connected={auth?.strava?.connected}
          connectUrl="/api/v1/auth/strava"
          description="Activities, heart rate streams, power data"
        />
      </Section>

      {/* ── Body metrics ─────────────────────────────────── */}
      <Section title="Body Metrics">
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
          Used to calculate your BMR and daily caloric targets.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-3)' }}>
          <Field label="Weight (kg)" value={form.weight_kg} onChange={v => setForm(f => ({ ...f, weight_kg: v }))} type="number" />
          <Field label="Height (cm)" value={form.height_cm} onChange={v => setForm(f => ({ ...f, height_cm: v }))} type="number" />
          <Field label="Age" value={form.age} onChange={v => setForm(f => ({ ...f, age: v }))} type="number" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
          <SelectField label="Sex" value={form.sex} onChange={v => setForm(f => ({ ...f, sex: v }))}
            options={[{ value: 'male', label: 'Male' }, { value: 'female', label: 'Female' }]} />
          <SelectField label="Dietary preference" value={form.dietary_preference} onChange={v => setForm(f => ({ ...f, dietary_preference: v }))}
            options={[
              { value: 'omnivore', label: 'Omnivore' },
              { value: 'vegetarian', label: 'Vegetarian' },
              { value: 'vegan', label: 'Vegan' },
            ]} />
        </div>
      </Section>

      {/* ── Performance baselines ────────────────────────── */}
      <Section title="Performance Baselines">
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
          Used for accurate TSS calculation. Leave blank if unknown — hrTSS will be used instead.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-3)' }}>
          <Field label="FTP (watts)" value={form.ftp_watts} onChange={v => setForm(f => ({ ...f, ftp_watts: v }))} type="number"
            hint="Functional Threshold Power — cycling" />
          <Field label="LTHR (bpm)" value={form.lthr_bpm} onChange={v => setForm(f => ({ ...f, lthr_bpm: v }))} type="number"
            hint="Lactate threshold HR — all sports" />
          <Field label="VO2max" value={form.vo2max} onChange={v => setForm(f => ({ ...f, vo2max: v }))} type="number"
            hint="From Polar or Garmin estimate" />
        </div>
      </Section>

      {/* ── Nutrition settings ───────────────────────────── */}
      <Section title="Nutrition Settings">
        <div style={{ maxWidth: 220 }}>
          <Field
            label="Protein target (g/kg body weight)"
            value={form.protein_target_per_kg}
            onChange={v => setForm(f => ({ ...f, protein_target_per_kg: v }))}
            type="number"
            hint="Athletes: 1.6–2.2 g/kg. Default 1.8"
          />
        </div>
      </Section>

      {/* ── Save ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <button
          onClick={handleSave}
          disabled={updateProfile.isPending}
          style={{
            padding: '10px 24px', fontSize: 14, fontWeight: 500,
            background: 'var(--accent)', color: 'var(--bg-base)',
            border: 'none', borderRadius: 'var(--radius-sm)',
            opacity: updateProfile.isPending ? 0.7 : 1,
          }}
        >
          {updateProfile.isPending ? 'Saving…' : 'Save settings'}
        </button>
        {saved && <span style={{ fontSize: 13, color: 'var(--positive)' }}>✓ Saved! Targets recalculating…</span>}
      </div>
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--bg-border)' }}>
        {title}
      </h2>
      <div>{children}</div>
    </div>
  )
}

function Field({ label, value, onChange, type = 'text', hint }: any) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%', padding: '8px 10px', fontSize: 13,
          background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
          outline: 'none',
        }}
      />
      {hint && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{hint}</div>}
    </div>
  )
}

function SelectField({ label, value, onChange, options }: any) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)} style={{
        width: '100%', padding: '8px 10px', fontSize: 13,
        background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
      }}>
        {options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

function ConnectionRow({ label, connected, connectUrl, description }: any) {
  const handleConnect = async () => {
    const res = await fetch(connectUrl)
    const data = await res.json()
    if (data.url) window.location.href = data.url
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
      padding: 'var(--space-4) 0',
      borderBottom: '1px solid var(--bg-border)',
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 500 }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{description}</div>
      </div>
      {connected ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--positive)' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--positive)', display: 'inline-block' }} />
          Connected
        </div>
      ) : (
        <button onClick={handleConnect} style={{
          padding: '7px 16px', fontSize: 13, fontWeight: 500,
          background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
          transition: 'border-color 0.15s',
        }}>
          Connect →
        </button>
      )}
    </div>
  )
}
