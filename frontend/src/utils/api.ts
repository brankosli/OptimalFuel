import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  status: () => api.get('/api/v1/auth/status'),
  polarAuthUrl: () => api.get('/api/v1/auth/polar'),
  stravaAuthUrl: () => api.get('/api/v1/auth/strava'),
}

// ─── Activities ───────────────────────────────────────────────────────────────
export const activitiesApi = {
  list: (params?: { from?: string; to?: string; sport?: string }) =>
    api.get('/api/v1/activities/', { params }),
}

// ─── Sleep ────────────────────────────────────────────────────────────────────
export const sleepApi = {
  list: (params?: { from?: string; to?: string }) =>
    api.get('/api/v1/sleep/', { params }),
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export const analyticsApi = {
  summaries: (params?: { from?: string; to?: string }) =>
    api.get('/api/v1/analytics/', { params }),
  today: () => api.get('/api/v1/analytics/today'),
}

// ─── Nutrition ────────────────────────────────────────────────────────────────
export const nutritionApi = {
  meals: (date: string) => api.get('/api/v1/nutrition/meals', { params: { date } }),
  logMeal: (meal: object) => api.post('/api/v1/nutrition/meals', meal),
  deleteMeal: (id: number) => api.delete(`/api/v1/nutrition/meals/${id}`),
}

// ─── Profile ──────────────────────────────────────────────────────────────────
export const profileApi = {
  get: () => api.get('/api/v1/profile/'),
  update: (data: object) => api.put('/api/v1/profile/', data),
}
