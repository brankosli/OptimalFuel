import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  useSegments, useSegmentEfforts,
  useRoutes, useRouteRides,
  useTriggerSegmentSync,
} from '@/hooks/useData'
import RouteMiniMap from '@/components/charts/RouteMiniMap'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })
}

function fmtDelta(seconds: number) {
  if (seconds === 0) return <span style={{ color: 'var(--positive)', fontWeight: 600 }}>PR</span>
  const sign = seconds > 0 ? '+' : ''
  return <span style={{ color: seconds > 0 ? 'var(--negative)' : 'var(--positive)' }}>{sign}{seconds}s</span>
}

const cellStyle: React.CSSProperties = {
  padding: '8px 12px', fontSize: 13, color: 'var(--text-primary)',
  borderBottom: '1px solid var(--bg-border)',
}
const headStyle: React.CSSProperties = {
  ...cellStyle, fontSize: 11, color: 'var(--text-secondary)',
  textTransform: 'uppercase', letterSpacing: 0.8, fontWeight: 600,
}

// ─── Segments tab ─────────────────────────────────────────────────────────────

function SegmentsTab() {
  const { data: segments = [], isLoading } = useSegments()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const { data: detail } = useSegmentEfforts(selectedId)
  const sync = useTriggerSegmentSync()

  const chartData = (detail?.efforts ?? []).map((e: any) => ({
    date: fmtDate(e.date),
    time: e.elapsed_time,
    watts: e.avg_watts,
    hr: e.avg_heart_rate,
    pr: e.is_pr,
  }))

  return (
    <div style={{ display: 'flex', gap: 'var(--space-6)', alignItems: 'flex-start' }}>
      {/* Segment list */}
      <div style={{ width: 340, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {isLoading ? 'Loading…' : `${segments.length} segments`}
          </span>
          <button
            onClick={() => sync.mutate()}
            disabled={sync.isPending}
            style={{
              fontSize: 12, padding: '4px 10px',
              background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
              borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)',
              opacity: sync.isPending ? 0.6 : 1,
            }}
          >
            {sync.isPending ? 'Syncing…' : 'Sync rides'}
          </button>
        </div>

        <div style={{ border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
          {segments.length === 0 && !isLoading && (
            <div style={{ padding: 'var(--space-8)', textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
              No segments yet. Click "Sync rides" to fetch data.
            </div>
          )}
          {segments.map((s: any) => (
            <div
              key={s.segment_id}
              onClick={() => setSelectedId(s.segment_id === selectedId ? null : s.segment_id)}
              style={{
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '1px solid var(--bg-border)',
                cursor: 'pointer',
                background: selectedId === s.segment_id ? 'var(--accent-muted)' : 'transparent',
                borderRight: selectedId === s.segment_id ? '2px solid var(--accent)' : '2px solid transparent',
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{s.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, display: 'flex', gap: 12 }}>
                <span>{s.attempt_count}x</span>
                <span>Best {s.best_time_fmt}</span>
                {s.avg_watts && <span>{Math.round(s.avg_watts)}W avg</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {!selectedId && (
          <div style={{ paddingTop: 60, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Select a segment to see your progress
          </div>
        )}

        {detail && selectedId && (
          <>
            <div style={{ marginBottom: 'var(--space-5)' }}>
              <h2 style={{ fontSize: 18, fontWeight: 600 }}>{detail.name}</h2>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                {detail.effort_count} efforts · Best {detail.best_time_fmt}
              </div>
            </div>

            {/* Time chart */}
            <div style={{ height: 200, marginBottom: 'var(--space-6)' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 16, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                  <YAxis
                    tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    tickFormatter={v => {
                      const m = Math.floor(v / 60)
                      const s = v % 60
                      return `${m}:${String(s).padStart(2, '0')}`
                    }}
                    domain={['auto', 'auto']}
                    reversed
                  />
                  <Tooltip
                    formatter={(v: number) => {
                      const m = Math.floor(v / 60)
                      const s = v % 60
                      return [`${m}:${String(s).padStart(2, '0')}`, 'Time']
                    }}
                    contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--bg-border)', fontSize: 12 }}
                  />
                  <ReferenceLine
                    y={detail.best_time_seconds}
                    stroke="var(--positive)"
                    strokeDasharray="4 4"
                    label={{ value: 'PR', position: 'right', fontSize: 11, fill: 'var(--positive)' }}
                  />
                  <Line
                    type="monotone" dataKey="time"
                    stroke="var(--accent)" strokeWidth={2}
                    dot={(props: any) => props.payload.pr
                      ? <circle cx={props.cx} cy={props.cy} r={5} fill="var(--positive)" stroke="none" />
                      : <circle cx={props.cx} cy={props.cy} r={3} fill="var(--accent)" stroke="none" />
                    }
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Efforts table */}
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Date', 'Time', 'vs Best', 'Avg W', 'Avg HR', 'Cadence'].map(h => (
                    <th key={h} style={{ ...headStyle, textAlign: 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...detail.efforts].reverse().map((e: any) => (
                  <tr key={e.effort_id} style={{ background: e.is_pr ? 'var(--accent-muted)' : 'transparent' }}>
                    <td style={cellStyle}>{fmtDate(e.date)}</td>
                    <td style={{ ...cellStyle, fontVariantNumeric: 'tabular-nums' }}>{e.elapsed_time_fmt}</td>
                    <td style={cellStyle}>{fmtDelta(e.delta_from_best)}</td>
                    <td style={cellStyle}>{e.avg_watts ? `${Math.round(e.avg_watts)}W` : '-'}</td>
                    <td style={cellStyle}>{e.avg_heart_rate ? `${Math.round(e.avg_heart_rate)} bpm` : '-'}</td>
                    <td style={cellStyle}>{e.avg_cadence ? `${Math.round(e.avg_cadence)} rpm` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Routes tab ───────────────────────────────────────────────────────────────

function RoutesTab() {
  const { data: routes = [], isLoading } = useRoutes()
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const { data: detail } = useRouteRides(selectedKey)

  const chartData = (detail?.rides ?? []).map((r: any) => ({
    date: fmtDate(r.date),
    duration: r.duration_seconds,
    watts: r.avg_power_watts,
    hr: r.avg_heart_rate,
  }))

  return (
    <div style={{ display: 'flex', gap: 'var(--space-6)', alignItems: 'flex-start' }}>
      {/* Route list */}
      <div style={{ width: 340, flexShrink: 0 }}>
        <div style={{ marginBottom: 'var(--space-4)', fontSize: 13, color: 'var(--text-secondary)' }}>
          {isLoading ? 'Loading…' : `${routes.length} routes (≥2 rides)`}
        </div>

        <div style={{ border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
          {routes.length === 0 && !isLoading && (
            <div style={{ padding: 'var(--space-8)', textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
              No repeated routes found yet. Ride the same route twice and sync.
            </div>
          )}
          {routes.map((r: any) => (
            <div
              key={r.route_key}
              onClick={() => setSelectedKey(r.route_key === selectedKey ? null : r.route_key)}
              style={{
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '1px solid var(--bg-border)',
                cursor: 'pointer',
                background: selectedKey === r.route_key ? 'var(--accent-muted)' : 'transparent',
                borderRight: selectedKey === r.route_key ? '2px solid var(--accent)' : '2px solid transparent',
                display: 'flex', gap: 'var(--space-3)', alignItems: 'center',
              }}
            >
              <RouteMiniMap polyline={r.summary_polyline} width={56} height={44} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {r.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, display: 'flex', gap: 12 }}>
                  <span>{r.attempt_count}x</span>
                  <span>{r.distance_km} km</span>
                  <span>Best {r.best_duration_fmt}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {!selectedKey && (
          <div style={{ paddingTop: 60, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Select a route to compare rides
          </div>
        )}

        {detail && selectedKey && (
          <>
            <div style={{ marginBottom: 'var(--space-5)', display: 'flex', gap: 'var(--space-5)', alignItems: 'flex-start' }}>
              <RouteMiniMap
                polyline={detail.rides?.[0]?.summary_polyline}
                width={120}
                height={90}
                strokeWidth={2}
              />
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 600 }}>{detail.name}</h2>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                  {detail.ride_count} rides · {detail.distance_km} km · Best {detail.best_duration_fmt}
                </div>
              </div>
            </div>

            {/* Duration chart */}
            <div style={{ height: 200, marginBottom: 'var(--space-6)' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 16, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                  <YAxis
                    tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    tickFormatter={v => {
                      const h = Math.floor(v / 3600)
                      const m = Math.floor((v % 3600) / 60)
                      return h ? `${h}h${m}m` : `${m}m`
                    }}
                    domain={['auto', 'auto']}
                    reversed
                  />
                  <Tooltip
                    formatter={(v: number) => {
                      const h = Math.floor(v / 3600)
                      const m = Math.floor((v % 3600) / 60)
                      const s = v % 60
                      return [h ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${m}:${String(s).padStart(2,'0')}`, 'Duration']
                    }}
                    contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--bg-border)', fontSize: 12 }}
                  />
                  <ReferenceLine
                    y={detail.best_duration_seconds}
                    stroke="var(--positive)"
                    strokeDasharray="4 4"
                    label={{ value: 'Best', position: 'right', fontSize: 11, fill: 'var(--positive)' }}
                  />
                  <Line type="monotone" dataKey="duration" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3, fill: 'var(--accent)' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Rides table */}
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Date', 'Name', 'Duration', 'vs Best', 'Avg W', 'NP', 'HR', 'TSS'].map(h => (
                    <th key={h} style={{ ...headStyle, textAlign: 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...detail.rides].reverse().map((r: any) => (
                  <tr key={r.id} style={{ background: r.delta_from_best === 0 ? 'var(--accent-muted)' : 'transparent' }}>
                    <td style={cellStyle}>{fmtDate(r.date)}</td>
                    <td style={{ ...cellStyle, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</td>
                    <td style={{ ...cellStyle, fontVariantNumeric: 'tabular-nums' }}>{r.duration_fmt}</td>
                    <td style={cellStyle}>{fmtDelta(r.delta_from_best)}</td>
                    <td style={cellStyle}>{r.avg_power_watts ? `${Math.round(r.avg_power_watts)}W` : '-'}</td>
                    <td style={cellStyle}>{r.normalized_power_watts ? `${Math.round(r.normalized_power_watts)}W` : '-'}</td>
                    <td style={cellStyle}>{r.avg_heart_rate ? `${r.avg_heart_rate} bpm` : '-'}</td>
                    <td style={cellStyle}>{r.tss ? Math.round(r.tss) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ComparisonPage() {
  const [tab, setTab] = useState<'segments' | 'routes'>('segments')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Comparison</h1>
        <div style={{ display: 'flex', gap: 2, background: 'var(--bg-elevated)', padding: 3, borderRadius: 'var(--radius-sm)' }}>
          {(['segments', 'routes'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: '5px 16px', fontSize: 13, fontWeight: tab === t ? 500 : 400,
                background: tab === t ? 'var(--bg-surface)' : 'transparent',
                border: 'none', borderRadius: 'var(--radius-sm)',
                color: tab === t ? 'var(--text-primary)' : 'var(--text-secondary)',
                textTransform: 'capitalize',
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === 'segments' ? <SegmentsTab /> : <RoutesTab />}
    </div>
  )
}
