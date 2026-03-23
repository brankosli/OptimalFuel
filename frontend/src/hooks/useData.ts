import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { analyticsApi, activitiesApi, sleepApi, nutritionApi, profileApi, authApi } from '@/utils/api'
import { format, subDays } from 'date-fns'

// ─── Auth ─────────────────────────────────────────────────────────────────────
export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth-status'],
    queryFn: () => authApi.status().then(r => r.data),
  })
}

// ─── Today's summary ──────────────────────────────────────────────────────────
export function useTodaySummary() {
  return useQuery({
    queryKey: ['analytics', 'today'],
    queryFn: () => analyticsApi.today().then(r => r.data),
    refetchInterval: 1000 * 60 * 10,  // re-fetch every 10 min
  })
}

// ─── PMC chart data ───────────────────────────────────────────────────────────
export function usePMC(days: number = 90) {
  const from = format(subDays(new Date(), days), 'yyyy-MM-dd')
  const to   = format(new Date(), 'yyyy-MM-dd')
  return useQuery({
    queryKey: ['analytics', 'pmc', days],
    queryFn: () => analyticsApi.summaries({ from, to }).then(r => r.data),
  })
}

// ─── Activities ───────────────────────────────────────────────────────────────
export function useActivities(days: number = 30) {
  const from = format(subDays(new Date(), days), 'yyyy-MM-dd')
  const to   = format(new Date(), 'yyyy-MM-dd')
  return useQuery({
    queryKey: ['activities', days],
    queryFn: () => activitiesApi.list({ from, to }).then(r => r.data),
  })
}

// ─── Sleep ────────────────────────────────────────────────────────────────────
export function useSleep(days: number = 30) {
  const from = format(subDays(new Date(), days), 'yyyy-MM-dd')
  const to   = format(new Date(), 'yyyy-MM-dd')
  return useQuery({
    queryKey: ['sleep', days],
    queryFn: () => sleepApi.list({ from, to }).then(r => r.data),
  })
}

// ─── Nutrition ────────────────────────────────────────────────────────────────
export function useMeals(date: string) {
  return useQuery({
    queryKey: ['meals', date],
    queryFn: () => nutritionApi.meals(date).then(r => r.data),
  })
}

export function useLogMeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (meal: object) => nutritionApi.logMeal(meal).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meals'] }),
  })
}

export function useDeleteMeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => nutritionApi.deleteMeal(id).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meals'] }),
  })
}

// ─── Profile ──────────────────────────────────────────────────────────────────
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => profileApi.get().then(r => r.data),
  })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: object) => profileApi.update(data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

// ─── Manual sync ──────────────────────────────────────────────────────────────
export function useTriggerSync() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => analyticsApi.summaries().then(r => r.data),   // placeholder
    onSuccess: () => qc.invalidateQueries(),
  })
}
