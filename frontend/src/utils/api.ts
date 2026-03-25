import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export const authApi = {
  status: () => api.get('/api/v1/auth/status'),
  polarAuthUrl: () => api.get('/api/v1/auth/polar'),
  stravaAuthUrl: () => api.get('/api/v1/auth/strava'),
}

export const activitiesApi = {
  list: (params?: { from?: string; to?: string; sport?: string }) =>
    api.get('/api/v1/activities/', { params }),
}

export const sleepApi = {
  list: (params?: { from?: string; to?: string }) =>
    api.get('/api/v1/sleep/', { params }),
}

export const analyticsApi = {
  summaries: (params?: { from?: string; to?: string }) =>
    api.get('/api/v1/analytics/', { params }),
  today: () => api.get('/api/v1/analytics/today'),
  weeklyReport: (weekOffset: number) =>
    api.get('/api/v1/analytics/weekly-report', { params: { week_offset: weekOffset } }),
  sleepInsights: (params?: { from?: string; to?: string }) =>
    api.get('/api/v1/analytics/sleep-insights', { params }),
}

export const nutritionApi = {
  meals: (date: string) => api.get('/api/v1/nutrition/meals', { params: { date } }),
  logMeal: (meal: object) => api.post('/api/v1/nutrition/meals', meal),
  deleteMeal: (id: number) => api.delete(`/api/v1/nutrition/meals/${id}`),
}

export const profileApi = {
  get: () => api.get('/api/v1/profile/'),
  update: (data: object) => api.put('/api/v1/profile/', data),
}

export const racesApi = {
  list:      ()                  => api.get('/api/v1/races/'),
  get:       (id: number)        => api.get(`/api/v1/races/${id}`),
  create:    (data: object)      => api.post('/api/v1/races/', data),
  update:    (id: number, data: object) => api.put(`/api/v1/races/${id}`, data),
  delete:    (id: number)        => api.delete(`/api/v1/races/${id}`),
  nextRace:  ()                  => api.get('/api/v1/races/dashboard/next'),
}
