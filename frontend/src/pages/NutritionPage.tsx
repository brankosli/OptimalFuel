import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { useTodaySummary, useMeals, useLogMeal, useDeleteMeal, useNextRace } from '@/hooks/useData'
import { carbStrategyLabel, carbStrategyColor } from '@/utils/format'
import MacroRing from '@/components/nutrition/MacroRing'
import { api } from '@/utils/api'

// ─── Types ────────────────────────────────────────────────────────────────────
interface FoodResult {
  food_id: string
  label: string
  category: string
  per_100g: { calories: number; carbs_g: number; protein_g: number; fat_g: number }
  measures: { label: string; weight: number }[]
}

interface MealRec {
  meal_type: string
  name: string
  description: string
  timing: string
  calories: number
  carbs_g: number
  protein_g: number
  fat_g: number
  why: string
}

interface AiRec {
  day_summary: string
  timing_note: string
  meals: MealRec[]
  hydration_note: string
  supplement_note?: string
  error?: string
}

// ─── Food search hook ─────────────────────────────────────────────────────────
function useFoodSearch(q: string) {
  const [results, setResults] = useState<FoodResult[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (q.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const r = await api.get('/api/v1/nutrition/food-search', { params: { q } })
        setResults(r.data.results ?? [])
      } catch { setResults([]) }
      finally { setLoading(false) }
    }, 400)
    return () => clearTimeout(timer)
  }, [q])

  return { results, loading }
}

// ─── Meal type emoji ──────────────────────────────────────────────────────────
function mealEmoji(type: string): string {
  const map: Record<string, string> = {
    breakfast: '🌅', lunch: '☀️', dinner: '🌙',
    snack: '🍎', pre_workout: '⚡', post_workout: '💪',
  }
  return map[type] ?? '🍽️'
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function NutritionPage() {
  const today = format(new Date(), 'yyyy-MM-dd')
  const { data: summary }    = useTodaySummary()
  const { data: meals = [] } = useMeals(today)
  const { data: nextRace }   = useNextRace()
  const logMeal    = useLogMeal()
  const deleteMeal = useDeleteMeal()

  const [tab, setTab]             = useState<'log' | 'recommend'>('log')
  const [showForm, setShowForm]   = useState(false)
  const [aiRec, setAiRec]         = useState<AiRec | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError]     = useState<string | null>(null)

  // Log form
  const [form, setForm] = useState({
    meal_type: 'breakfast', name: '', calories: '',
    carbs_g: '', protein_g: '', fat_g: '',
  })
  const [foodSearch, setFoodSearch]     = useState('')
  const [selectedFood, setSelectedFood] = useState<FoodResult | null>(null)
  const [quantity, setQuantity]         = useState('100')
  const { results: foodResults, loading: foodLoading } = useFoodSearch(foodSearch)

  // Logged totals
  const logged = {
    calories: sum(meals, 'calories'),
    carbs:    sum(meals, 'carbs_g'),
    protein:  sum(meals, 'protein_g'),
    fat:      sum(meals, 'fat_g'),
  }

  function applyFood(food: FoodResult) {
    const scale = (parseFloat(quantity) || 100) / 100
    setForm(f => ({
      ...f,
      name:      food.label,
      calories:  (food.per_100g.calories  * scale).toFixed(0),
      carbs_g:   (food.per_100g.carbs_g   * scale).toFixed(1),
      protein_g: (food.per_100g.protein_g * scale).toFixed(1),
      fat_g:     (food.per_100g.fat_g     * scale).toFixed(1),
    }))
    setSelectedFood(food)
    setFoodSearch('')
  }

  function recalcForQuantity(q: string, food: FoodResult) {
    const scale = (parseFloat(q) || 100) / 100
    setForm(f => ({
      ...f,
      calories:  (food.per_100g.calories  * scale).toFixed(0),
      carbs_g:   (food.per_100g.carbs_g   * scale).toFixed(1),
      protein_g: (food.per_100g.protein_g * scale).toFixed(1),
      fat_g:     (food.per_100g.fat_g     * scale).toFixed(1),
    }))
  }

  async function handleSubmit() {
    if (!form.name) return
    await logMeal.mutateAsync({
      log_date: today, meal_type: form.meal_type, name: form.name,
      calories:  form.calories  ? +form.calories  : null,
      carbs_g:   form.carbs_g   ? +form.carbs_g   : null,
      protein_g: form.protein_g ? +form.protein_g : null,
      fat_g:     form.fat_g     ? +form.fat_g     : null,
    })
    setForm({ meal_type: 'breakfast', name: '', calories: '', carbs_g: '', protein_g: '', fat_g: '' })
    setSelectedFood(null)
    setFoodSearch('')
    setShowForm(false)
  }

  // ── AI recommendations — calls backend which calls Anthropic ────────────────
  async function loadRecommendations() {
    setAiLoading(true)
    setAiError(null)
    try {
      const r = await api.get('/api/v1/nutrition/recommendations')
      if (r.data.error) {
        setAiError(r.data.error)
      } else {
        setAiRec(r.data)
      }
    } catch (e: any) {
      setAiError(`Could not load recommendations: ${e.message}`)
    } finally {
      setAiLoading(false)
    }
  }

  async function logRecommended(meal: MealRec) {
    await logMeal.mutateAsync({
      log_date:  today,
      meal_type: meal.meal_type.replace('_', ' '),
      name:      meal.name,
      calories:  meal.calories,
      carbs_g:   meal.carbs_g,
      protein_g: meal.protein_g,
      fat_g:     meal.fat_g,
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>

      <h1 style={{ fontSize: 20, fontWeight: 600 }}>
        Nutrition — {format(new Date(), 'EEEE, MMM d')}
      </h1>

      {/* ── Targets + progress ─────────────────────────── */}
      {summary?.target_calories ? (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-6)' }}>
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <MacroRing
                carbs={summary.target_carbs_g ?? 0}
                protein={summary.target_protein_g ?? 0}
                fat={summary.target_fat_g ?? 0}
                size={100}
              />
              <div style={{ position: 'absolute', inset: 0, display: 'flex',
                flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 15, fontWeight: 700,
                  fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
                  {Math.round(summary.target_calories)}
                </span>
                <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>kcal</span>
              </div>
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 'var(--space-4)',
                color: carbStrategyColor(summary.carb_strategy) }}>
                {carbStrategyLabel(summary.carb_strategy)}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-3)' }}>
                <MacroTarget label="Carbs"   target={summary.target_carbs_g}
                  logged={logged.carbs}   color="var(--accent)" />
                <MacroTarget label="Protein" target={summary.target_protein_g}
                  logged={logged.protein} color="var(--info)" />
                <MacroTarget label="Fat"     target={summary.target_fat_g}
                  logged={logged.fat}     color="var(--warning)" />
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>
                Logged
              </div>
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

      {/* Race proximity alert */}
      {nextRace?.plan?.days_out != null && nextRace.plan.days_out <= 14 && (
        <div style={{
          padding: '10px 16px', borderRadius: 'var(--radius-sm)',
          background: 'rgba(232,255,71,0.08)', border: '1px solid var(--accent)40',
          fontSize: 12, color: 'var(--text-secondary)',
        }}>
          🏁 <strong style={{ color: 'var(--accent)' }}>{nextRace.name}</strong> is{' '}
          {nextRace.plan.days_out} days away —{' '}
          {nextRace.plan.days_out <= 3
            ? 'Race week: focus on carb loading and hydration'
            : 'Start prioritising carbs and reducing fibre this week'}
        </div>
      )}

      {/* ── Tabs ──────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 4 }}>
        {[
          { key: 'log',       label: '📋 Meal Log' },
          { key: 'recommend', label: '🤖 AI Recommendations' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as any)} style={{
            padding: '8px 16px', fontSize: 13, borderRadius: 'var(--radius-sm)',
            border: '1px solid',
            borderColor: tab === t.key ? 'var(--accent)' : 'var(--bg-border)',
            background:  tab === t.key ? 'var(--accent-muted)' : 'var(--bg-elevated)',
            color:       tab === t.key ? 'var(--accent)' : 'var(--text-secondary)',
            fontWeight:  tab === t.key ? 600 : 400, cursor: 'pointer',
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Meal Log tab ──────────────────────────────── */}
      {tab === 'log' && (
        <>
          <div style={{ display: 'flex', alignItems: 'center',
            justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)',
              textTransform: 'uppercase', letterSpacing: 1 }}>
              Today's Meals
            </h3>
            <button onClick={() => setShowForm(!showForm)} style={saveBtnStyle}>
              + Log meal
            </button>
          </div>

          {showForm && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column',
              gap: 'var(--space-4)' }}>

              {/* Food search */}
              <div>
                <label style={labelStyle}>Search food database</label>
                <div style={{ position: 'relative' }}>
                  <input
                    placeholder="Type a food name (e.g. chicken breast, oats, banana)…"
                    value={foodSearch}
                    onChange={e => { setFoodSearch(e.target.value); setSelectedFood(null) }}
                    style={inputStyle}
                  />
                  {foodLoading && (
                    <span style={{ position: 'absolute', right: 10, top: '50%',
                      transform: 'translateY(-50%)', fontSize: 11,
                      color: 'var(--text-muted)' }}>
                      Searching…
                    </span>
                  )}
                </div>

                {foodResults.length > 0 && !selectedFood && (
                  <div style={{ border: '1px solid var(--bg-border)', marginTop: 4,
                    borderRadius: 'var(--radius-sm)', background: 'var(--bg-surface)',
                    maxHeight: 260, overflowY: 'auto' }}>
                    {foodResults.map(food => (
                      <div key={food.food_id} onClick={() => applyFood(food)}
                        style={{ padding: '10px 14px', cursor: 'pointer',
                          display: 'flex', alignItems: 'center',
                          justifyContent: 'space-between',
                          borderBottom: '1px solid var(--bg-border)' }}
                        onMouseEnter={e =>
                          (e.currentTarget.style.background = 'var(--bg-elevated)')}
                        onMouseLeave={e =>
                          (e.currentTarget.style.background = 'transparent')}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>{food.label}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {food.category}
                          </div>
                        </div>
                        <div style={{ fontSize: 11, textAlign: 'right',
                          fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                          <div>{food.per_100g.calories} kcal</div>
                          <div style={{ color: 'var(--text-muted)' }}>per 100g</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {selectedFood && (
                  <div style={{ marginTop: 8, padding: '10px 14px',
                    background: 'var(--accent-muted)', borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--accent)40',
                    display: 'flex', alignItems: 'center',
                    justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)' }}>
                        ✓ {selectedFood.label}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                        Macros calculated for {quantity}g
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input type="number" value={quantity}
                        onChange={e => {
                          setQuantity(e.target.value)
                          recalcForQuantity(e.target.value, selectedFood)
                        }}
                        style={{ ...inputStyle, width: 70, textAlign: 'center' }} />
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>g</span>
                      <button onClick={() => { setSelectedFood(null); setFoodSearch('') }}
                        style={{ background: 'none', border: 'none',
                          color: 'var(--text-muted)', fontSize: 18, cursor: 'pointer' }}>
                        ×
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr',
                gap: 'var(--space-3)' }}>
                <div>
                  <label style={labelStyle}>Meal type</label>
                  <select value={form.meal_type}
                    onChange={e => setForm(f => ({ ...f, meal_type: e.target.value }))}
                    style={inputStyle}>
                    {['breakfast', 'lunch', 'dinner', 'snack'].map(o =>
                      <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Name *</label>
                  <input placeholder="Meal name" value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    style={inputStyle} />
                </div>
              </div>

              <div>
                <label style={labelStyle}>
                  Macros
                  {selectedFood
                    ? ' (auto-filled — adjust quantity above)'
                    : ' (enter manually or use food search above)'}
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: 'var(--space-3)' }}>
                  {[
                    { key: 'calories',  label: 'Calories',   color: 'var(--text-primary)' },
                    { key: 'carbs_g',   label: 'Carbs (g)',  color: 'var(--accent)' },
                    { key: 'protein_g', label: 'Protein (g)', color: 'var(--info)' },
                    { key: 'fat_g',     label: 'Fat (g)',    color: 'var(--warning)' },
                  ].map(field => (
                    <div key={field.key}>
                      <div style={{ fontSize: 10, color: field.color, fontWeight: 500,
                        textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                        {field.label}
                      </div>
                      <input type="number" value={(form as any)[field.key]}
                        onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                        style={{ ...inputStyle, fontFamily: 'var(--font-mono)' }} />
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 'var(--space-2)',
                justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowForm(false)
                    setSelectedFood(null)
                    setFoodSearch('')
                  }}
                  style={cancelBtnStyle}>
                  Cancel
                </button>
                <button onClick={handleSubmit} disabled={!form.name} style={saveBtnStyle}>
                  Save meal
                </button>
              </div>
            </div>
          )}

          {meals.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              No meals logged yet today.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {meals.map((m: any) => (
                <div key={m.id} className="card-sm" style={{ display: 'flex',
                  alignItems: 'center', gap: 'var(--space-4)' }}>
                  <div style={{ fontSize: 11, padding: '3px 8px', borderRadius: 4,
                    background: 'var(--bg-border)', color: 'var(--text-muted)',
                    textTransform: 'capitalize', flexShrink: 0 }}>
                    {m.meal_type}
                  </div>
                  <div style={{ flex: 1, fontSize: 14, fontWeight: 500 }}>{m.name}</div>
                  <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 12,
                    color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    {m.calories  && <span>{Math.round(m.calories)} kcal</span>}
                    {m.carbs_g   && <span style={{ color: 'var(--accent)' }}>C {Math.round(m.carbs_g)}g</span>}
                    {m.protein_g && <span style={{ color: 'var(--info)' }}>P {Math.round(m.protein_g)}g</span>}
                    {m.fat_g     && <span style={{ color: 'var(--warning)' }}>F {Math.round(m.fat_g)}g</span>}
                  </div>
                  <button onClick={() => deleteMeal.mutate(m.id)}
                    style={{ background: 'none', border: 'none',
                      color: 'var(--text-muted)', fontSize: 18,
                      padding: 4, lineHeight: 1, cursor: 'pointer' }}>
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── AI Recommendations tab ────────────────────── */}
      {tab === 'recommend' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>

          {!aiRec && !aiLoading && !aiError && (
            <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)' }}>
              <div style={{ fontSize: 32, marginBottom: 'var(--space-4)' }}>🤖</div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>
                AI-Powered Meal Recommendations
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)',
                maxWidth: 420, margin: '0 auto var(--space-6)', lineHeight: 1.6 }}>
                Generates a personalised meal plan based on your training load,
                recovery status, macro targets and race calendar.
              </div>
              <button onClick={loadRecommendations}
                style={{ ...saveBtnStyle, padding: '10px 28px', fontSize: 14 }}>
                Generate Today's Meal Plan
              </button>
            </div>
          )}

          {aiLoading && (
            <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)',
              color: 'var(--text-muted)', fontSize: 13 }}>
              <div style={{ fontSize: 24, marginBottom: 12 }}>⏳</div>
              Generating personalised meal plan based on your training data…
            </div>
          )}

          {aiError && (
            <div className="card" style={{ color: 'var(--negative)', fontSize: 13,
              display: 'flex', alignItems: 'center', gap: 12 }}>
              {aiError}
              <button onClick={loadRecommendations}
                style={{ ...cancelBtnStyle, fontSize: 12 }}>
                Try again
              </button>
            </div>
          )}

          {aiRec && !aiError && (
            <>
              {/* Day summary */}
              <div className="card" style={{ borderColor: 'var(--accent)40',
                background: 'rgba(232,255,71,0.04)' }}>
                <div style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
                  letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Today's Nutrition Focus
                </div>
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>
                  {aiRec.day_summary}
                </div>
                {aiRec.timing_note && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)',
                    padding: '8px 12px', background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    borderLeft: '3px solid var(--accent)' }}>
                    ⏰ {aiRec.timing_note}
                  </div>
                )}
              </div>

              {/* Meal cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {aiRec.meals.map((meal, i) => (
                  <div key={i} className="card"
                    style={{ padding: 'var(--space-4) var(--space-5)' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start',
                      justifyContent: 'space-between', gap: 'var(--space-4)' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center',
                          gap: 8, marginBottom: 4 }}>
                          <span style={{ fontSize: 20 }}>{mealEmoji(meal.meal_type)}</span>
                          <span style={{ fontSize: 14, fontWeight: 600 }}>{meal.name}</span>
                          <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3,
                            background: 'var(--bg-elevated)', color: 'var(--text-muted)',
                            textTransform: 'capitalize' }}>
                            {meal.meal_type.replace('_', ' ')}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)',
                          marginBottom: 4 }}>
                          {meal.description}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)',
                          fontStyle: 'italic', marginBottom: 6 }}>
                          {meal.why}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 500 }}>
                          ⏰ {meal.timing}
                        </div>
                      </div>

                      <div style={{ flexShrink: 0, textAlign: 'right' }}>
                        <div style={{ fontSize: 16, fontWeight: 700,
                          fontFamily: 'var(--font-mono)' }}>
                          {meal.calories} kcal
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)',
                          fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                          <span style={{ color: 'var(--accent)' }}>C{meal.carbs_g}g</span>
                          {' · '}
                          <span style={{ color: 'var(--info)' }}>P{meal.protein_g}g</span>
                          {' · '}
                          <span style={{ color: 'var(--warning)' }}>F{meal.fat_g}g</span>
                        </div>
                        <button onClick={() => logRecommended(meal)}
                          style={{ marginTop: 8, padding: '4px 12px', fontSize: 11,
                            background: 'var(--accent)', color: '#000', border: 'none',
                            borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>
                          + Log this
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Hydration + supplements */}
              <div style={{ display: 'grid',
                gridTemplateColumns: aiRec.supplement_note ? '1fr 1fr' : '1fr',
                gap: 'var(--space-3)' }}>
                {aiRec.hydration_note && (
                  <div className="card-sm" style={{ borderLeft: '3px solid var(--info)' }}>
                    <div style={{ fontSize: 10, color: 'var(--info)',
                      textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                      💧 Hydration
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {aiRec.hydration_note}
                    </div>
                  </div>
                )}
                {aiRec.supplement_note && (
                  <div className="card-sm" style={{ borderLeft: '3px solid var(--warning)' }}>
                    <div style={{ fontSize: 10, color: 'var(--warning)',
                      textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                      💊 Supplements
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {aiRec.supplement_note}
                    </div>
                  </div>
                )}
              </div>

              <button onClick={loadRecommendations}
                style={{ ...cancelBtnStyle, alignSelf: 'flex-start' }}>
                ↺ Regenerate plan
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function MacroTarget({ label, target, logged, color }: any) {
  const pct = target ? Math.min(logged / target, 1) : 0
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between',
        fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', color }}>
          {Math.round(logged)}/{Math.round(target ?? 0)}g
        </span>
      </div>
      <div style={{ height: 4, background: 'var(--bg-border)', borderRadius: 2 }}>
        <div style={{ height: '100%', width: `${pct * 100}%`, background: color,
          borderRadius: 2, transition: 'width 0.3s' }} />
      </div>
    </div>
  )
}

function sum(items: any[], key: string): number {
  return items.reduce((acc, m) => acc + (m[key] ?? 0), 0)
}

const inputStyle: React.CSSProperties = {
  padding: '8px 10px', fontSize: 13, width: '100%',
  background: 'var(--bg-base)', border: '1px solid var(--bg-border)',
  borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase',
  letterSpacing: 0.5, display: 'block', marginBottom: 5,
}

const saveBtnStyle: React.CSSProperties = {
  padding: '7px 16px', fontSize: 13, fontWeight: 500,
  background: 'var(--accent)', color: 'var(--bg-base)',
  border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
}

const cancelBtnStyle: React.CSSProperties = {
  padding: '7px 16px', fontSize: 13, background: 'transparent',
  color: 'var(--text-secondary)', border: '1px solid var(--bg-border)',
  borderRadius: 'var(--radius-sm)', cursor: 'pointer',
}
