import { useState } from 'react'
import { format } from 'date-fns'
import { useTodaySummary, useMeals, useLogMeal, useDeleteMeal } from '@/hooks/useData'
import { carbStrategyLabel, carbStrategyColor } from '@/utils/format'
import MacroRing from '@/components/nutrition/MacroRing'

export default function NutritionPage() {
  const today = format(new Date(), 'yyyy-MM-dd')
  const { data: summary } = useTodaySummary()
  const { data: meals = [] } = useMeals(today)
  const logMeal = useLogMeal()
  const deleteMeal = useDeleteMeal()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    meal_type: 'breakfast',
    name: '',
    calories: '',
    carbs_g: '',
    protein_g: '',
    fat_g: '',
  })

  // Sum logged macros
  const logged = {
    calories: sum(meals, 'calories'),
    carbs: sum(meals, 'carbs_g'),
    protein: sum(meals, 'protein_g'),
    fat: sum(meals, 'fat_g'),
  }

  const handleSubmit = async () => {
    if (!form.name) return
    await logMeal.mutateAsync({
      log_date: today,
      meal_type: form.meal_type,
      name: form.name,
      calories: form.calories ? +form.calories : null,
      carbs_g: form.carbs_g ? +form.carbs_g : null,
      protein_g: form.protein_g ? +form.protein_g : null,
      fat_g: form.fat_g ? +form.fat_g : null,
    })
    setForm({ meal_type: 'breakfast', name: '', calories: '', carbs_g: '', protein_g: '', fat_g: '' })
    setShowForm(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Nutrition — {format(new Date(), 'EEEE, MMM d')}</h1>

      {/* ── Targets + progress ──────────────────────────── */}
      {summary?.target_calories ? (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-6)' }}>
            {/* Ring */}
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <MacroRing
                carbs={summary.target_carbs_g ?? 0}
                protein={summary.target_protein_g ?? 0}
                fat={summary.target_fat_g ?? 0}
                size={100}
              />
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontSize: 15, fontWeight: 700, fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
                  {Math.round(summary.target_calories)}
                </span>
                <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>kcal</span>
              </div>
            </div>

            {/* Targets */}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: carbStrategyColor(summary.carb_strategy), marginBottom: 'var(--space-4)' }}>
                {carbStrategyLabel(summary.carb_strategy)}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-3)' }}>
                <MacroTarget label="Carbs"   target={summary.target_carbs_g}   logged={logged.carbs}   color="var(--accent)" />
                <MacroTarget label="Protein" target={summary.target_protein_g} logged={logged.protein} color="var(--info)" />
                <MacroTarget label="Fat"     target={summary.target_fat_g}     logged={logged.fat}     color="var(--warning)" />
              </div>
            </div>

            {/* Calories logged */}
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Logged</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                {Math.round(logged.calories)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {Math.round(summary.target_calories - logged.calories)} remaining
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Complete your profile to see personalised nutrition targets.
        </div>
      )}

      {/* ── Meal log ────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>
          Today's Meals
        </h3>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            padding: '7px 14px', fontSize: 13, fontWeight: 500,
            background: 'var(--accent)', color: 'var(--bg-base)',
            border: 'none', borderRadius: 'var(--radius-sm)', transition: 'opacity 0.15s',
          }}
        >
          + Log meal
        </button>
      </div>

      {/* Add meal form */}
      {showForm && (
        <div className="card-sm" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 'var(--space-3)' }}>
            <Select value={form.meal_type} onChange={v => setForm(f => ({ ...f, meal_type: v }))}
              options={['breakfast', 'lunch', 'dinner', 'snack']} />
            <Input placeholder="Meal name *" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
            <Input placeholder="Calories" type="number" value={form.calories} onChange={v => setForm(f => ({ ...f, calories: v }))} />
            <Input placeholder="Carbs (g)" type="number" value={form.carbs_g} onChange={v => setForm(f => ({ ...f, carbs_g: v }))} />
            <Input placeholder="Protein (g)" type="number" value={form.protein_g} onChange={v => setForm(f => ({ ...f, protein_g: v }))} />
            <Input placeholder="Fat (g)" type="number" value={form.fat_g} onChange={v => setForm(f => ({ ...f, fat_g: v }))} />
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
            <button onClick={() => setShowForm(false)} style={cancelBtnStyle}>Cancel</button>
            <button onClick={handleSubmit} disabled={!form.name} style={saveBtnStyle}>Save</button>
          </div>
        </div>
      )}

      {/* Meal list grouped by type */}
      {meals.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No meals logged yet today.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {meals.map((m: any) => (
            <div key={m.id} className="card-sm" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
              <div style={{
                fontSize: 11, padding: '3px 8px', borderRadius: 4,
                background: 'var(--bg-border)', color: 'var(--text-muted)',
                textTransform: 'capitalize', flexShrink: 0,
              }}>
                {m.meal_type}
              </div>
              <div style={{ flex: 1, fontSize: 14, fontWeight: 500 }}>{m.name}</div>
              <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {m.calories && <span>{Math.round(m.calories)} kcal</span>}
                {m.carbs_g && <span style={{ color: 'var(--accent)' }}>C {Math.round(m.carbs_g)}g</span>}
                {m.protein_g && <span style={{ color: 'var(--info)' }}>P {Math.round(m.protein_g)}g</span>}
                {m.fat_g && <span style={{ color: 'var(--warning)' }}>F {Math.round(m.fat_g)}g</span>}
              </div>
              <button
                onClick={() => deleteMeal.mutate(m.id)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: 16, padding: 4, lineHeight: 1 }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function MacroTarget({ label, target, logged, color }: any) {
  const pct = target ? Math.min(logged / target, 1) : 0
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', color }}>
          {Math.round(logged)}/{Math.round(target ?? 0)}g
        </span>
      </div>
      <div style={{ height: 4, background: 'var(--bg-border)', borderRadius: 2 }}>
        <div style={{ height: '100%', width: `${pct * 100}%`, background: color, borderRadius: 2, transition: 'width 0.3s' }} />
      </div>
    </div>
  )
}

function Input({ placeholder, value, onChange, type = 'text' }: any) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        padding: '8px 10px', fontSize: 13, width: '100%',
        background: 'var(--bg-base)', border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
        outline: 'none',
      }}
    />
  )
}

function Select({ value, onChange, options }: any) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} style={{
      padding: '8px 10px', fontSize: 13,
      background: 'var(--bg-base)', border: '1px solid var(--bg-border)',
      borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
    }}>
      {options.map((o: string) => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

function sum(items: any[], key: string): number {
  return items.reduce((acc, m) => acc + (m[key] ?? 0), 0)
}

const saveBtnStyle: React.CSSProperties = {
  padding: '7px 16px', fontSize: 13, fontWeight: 500,
  background: 'var(--accent)', color: 'var(--bg-base)',
  border: 'none', borderRadius: 'var(--radius-sm)',
}

const cancelBtnStyle: React.CSSProperties = {
  padding: '7px 16px', fontSize: 13,
  background: 'transparent', color: 'var(--text-secondary)',
  border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)',
}
