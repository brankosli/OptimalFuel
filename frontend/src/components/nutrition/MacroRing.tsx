interface MacroRingProps {
  carbs: number
  protein: number
  fat: number
  size?: number
}

export default function MacroRing({ carbs, protein, fat, size = 80 }: MacroRingProps) {
  const total = carbs + protein + fat
  if (!total) return null

  const r = (size - 10) / 2
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * r

  const carbPct    = carbs / total
  const proteinPct = protein / total
  const fatPct     = fat / total

  // Convert to stroke-dasharray segments
  const segments = [
    { pct: carbPct,    color: 'var(--accent)',    label: 'Carbs' },
    { pct: proteinPct, color: 'var(--info)',      label: 'Protein' },
    { pct: fatPct,     color: 'var(--warning)',   label: 'Fat' },
  ]

  let offset = 0
  const rings = segments.map(seg => {
    const dashLength = seg.pct * circumference
    const gapLength  = circumference - dashLength
    const ringOffset = offset
    offset += dashLength
    return { ...seg, dashLength, gapLength, ringOffset }
  })

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
      {/* Background track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bg-border)" strokeWidth={8} />

      {rings.map((seg, i) => (
        <circle
          key={i}
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={seg.color}
          strokeWidth={8}
          strokeDasharray={`${seg.dashLength} ${seg.gapLength}`}
          strokeDashoffset={-seg.ringOffset}
          strokeLinecap="butt"
        />
      ))}
    </svg>
  )
}
