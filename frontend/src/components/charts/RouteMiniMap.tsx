import { useMemo } from 'react'
import { polylineToSvgPath } from '@/utils/polyline'

interface Props {
  polyline: string | null | undefined
  width?: number
  height?: number
  color?: string
  strokeWidth?: number
}

export default function RouteMiniMap({
  polyline,
  width = 80,
  height = 60,
  color = 'var(--accent)',
  strokeWidth = 1.5,
}: Props) {
  const path = useMemo(
    () => (polyline ? polylineToSvgPath(polyline, width, height) : null),
    [polyline, width, height],
  )

  if (!path) {
    return (
      <div style={{
        width, height,
        background: 'var(--bg-elevated)',
        borderRadius: 4,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 10, color: 'var(--text-muted)',
      }}>
        no map
      </div>
    )
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: 'block', borderRadius: 4, background: 'var(--bg-elevated)', flexShrink: 0 }}
    >
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
