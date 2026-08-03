interface SparklineProps {
  points: number[]
  color: string
  height?: number
}

/** A tiny trend line with an emphasized endpoint — same treatment as any other chart in the app. */
export function Sparkline({ points, color, height = 24 }: SparklineProps) {
  const width = 100
  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1
  const coords = points.map((value, i) => {
    const x = (i / (points.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return [x, y] as const
  })
  const last = coords[coords.length - 1]

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polyline
        points={coords.map(([x, y]) => `${x},${y}`).join(' ')}
        fill="none"
        stroke={color}
        strokeWidth={1.6}
      />
      <circle cx={last[0]} cy={last[1]} r={2.4} fill={color} />
    </svg>
  )
}
