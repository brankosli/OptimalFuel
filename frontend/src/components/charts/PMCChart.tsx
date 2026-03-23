import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { usePMC } from '@/hooks/useData'
import { format, parseISO } from 'date-fns'

export default function PMCChart({ days = 90 }: { days?: number }) {
  const { data = [], isLoading } = usePMC(days)

  if (isLoading) {
    return <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading chart data…</div>
  }

  if (!data.length) {
    return <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No data yet — connect Polar or Strava to get started</div>
  }

  const formatted = data.map((d: any) => ({
    ...d,
    label: format(parseISO(d.date), 'MMM d'),
    tss: d.total_tss ?? 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={formatted} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          interval={Math.floor(formatted.length / 8)}
        />
        <YAxis
          yAxisId="load"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={32}
        />
        <YAxis
          yAxisId="tss"
          orientation="right"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={32}
        />

        <Tooltip
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--bg-border)',
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: 'var(--text-primary)', fontWeight: 500, marginBottom: 4 }}
          formatter={(value: number, name: string) => [
            typeof value === 'number' ? value.toFixed(1) : value,
            name,
          ]}
        />

        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)', paddingTop: 12 }}
        />

        <ReferenceLine yAxisId="load" y={0} stroke="var(--bg-border)" />

        {/* Daily TSS bars */}
        <Bar
          yAxisId="tss"
          dataKey="tss"
          name="TSS"
          fill="var(--accent-muted)"
          stroke="var(--accent)"
          strokeWidth={0.5}
          maxBarSize={6}
          radius={[2, 2, 0, 0]}
        />

        {/* CTL — Fitness (slow moving, chronic) */}
        <Line
          yAxisId="load"
          type="monotone"
          dataKey="ctl"
          name="CTL (Fitness)"
          stroke="var(--positive)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />

        {/* ATL — Fatigue (fast moving, acute) */}
        <Line
          yAxisId="load"
          type="monotone"
          dataKey="atl"
          name="ATL (Fatigue)"
          stroke="var(--negative)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />

        {/* TSB — Form (CTL - ATL) */}
        <Line
          yAxisId="load"
          type="monotone"
          dataKey="tsb"
          name="TSB (Form)"
          stroke="var(--accent)"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
