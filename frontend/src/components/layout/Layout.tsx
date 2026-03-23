import { Outlet, NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { authApi } from '@/utils/api'

const NAV = [
  { to: '/dashboard', label: 'Dashboard',  icon: '⚡' },
  { to: '/training',  label: 'Training',   icon: '🏃' },
  { to: '/sleep',     label: 'Sleep',      icon: '🌙' },
  { to: '/nutrition', label: 'Nutrition',  icon: '🥗' },
  { to: '/settings',  label: 'Settings',   icon: '⚙️' },
]

export default function Layout() {
  const { data: authStatus } = useQuery({
    queryKey: ['auth-status'],
    queryFn: () => authApi.status().then(r => r.data),
    staleTime: 1000 * 60,
  })

  const polarOk  = authStatus?.polar?.connected
  const stravaOk = authStatus?.strava?.connected

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── Sidebar ────────────────────────────────────────── */}
      <aside style={{
        width: 'var(--sidebar-width)',
        flexShrink: 0,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--bg-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--space-6) 0',
      }}>
        {/* Logo */}
        <div style={{ padding: '0 var(--space-6) var(--space-8)' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 500,
            fontSize: 16,
            color: 'var(--accent)',
            letterSpacing: '-0.5px',
          }}>
            OPTIMAL<span style={{ color: 'var(--text-secondary)' }}>FUEL</span>
          </span>
        </div>

        {/* Nav links */}
        <nav style={{ flex: 1 }}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-3) var(--space-6)',
                fontSize: 14,
                fontWeight: isActive ? 500 : 400,
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-muted)' : 'transparent',
                borderRight: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                transition: 'all 0.15s',
              })}
            >
              <span style={{ fontSize: 16 }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Connection status badges */}
        <div style={{
          padding: 'var(--space-6)',
          borderTop: '1px solid var(--bg-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-2)',
        }}>
          <ConnectionBadge label="Polar" connected={polarOk} />
          <ConnectionBadge label="Strava" connected={stravaOk} />
        </div>
      </aside>

      {/* ── Main content ───────────────────────────────────── */}
      <main style={{
        flex: 1,
        overflow: 'auto',
        padding: 'var(--space-8)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-6)',
      }}>
        <Outlet />
      </main>
    </div>
  )
}

function ConnectionBadge({ label, connected }: { label: string; connected?: boolean }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      fontSize: 12,
      color: 'var(--text-secondary)',
    }}>
      <span>{label}</span>
      <span style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        color: connected ? 'var(--positive)' : 'var(--text-muted)',
      }}>
        <span style={{
          width: 6, height: 6,
          borderRadius: '50%',
          background: connected ? 'var(--positive)' : 'var(--text-muted)',
          display: 'inline-block',
        }} />
        {connected ? 'live' : 'off'}
      </span>
    </div>
  )
}
