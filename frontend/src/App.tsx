import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import DashboardPage from '@/pages/DashboardPage'
import TrainingPage from '@/pages/TrainingPage'
import SleepPage from '@/pages/SleepPage'
import NutritionPage from '@/pages/NutritionPage'
import SettingsPage from '@/pages/SettingsPage'
import ReportPage from '@/pages/ReportPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"  element={<DashboardPage />} />
          <Route path="training"   element={<TrainingPage />} />
          <Route path="sleep"      element={<SleepPage />} />
          <Route path="nutrition"  element={<NutritionPage />} />
          <Route path="settings"   element={<SettingsPage />} />
          <Route path="report"     element={<ReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
