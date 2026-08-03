import { Card } from '@/components/ui/card'
import { Sparkline } from '@/features/dashboard/sparkline'

interface StatTileProps {
  label: string
  value: string
  points: number[]
  color: string
  delta?: string
  deltaTone?: 'up' | 'down' | 'neutral'
  note?: string
}

export function StatTile({ label, value, points, color, delta, deltaTone = 'neutral', note }: StatTileProps) {
  return (
    <Card className="p-4 pb-3.5">
      <div className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
        {label}
      </div>
      <div className="text-[26px] font-semibold tracking-tight">{value}</div>
      <Sparkline points={points} color={color} />
      {delta && (
        <div className="mt-1 flex items-center justify-between">
          <span
            className={
              'font-mono text-xs ' +
              (deltaTone === 'up' ? 'text-good-text' : deltaTone === 'down' ? 'text-critical-text' : 'text-fg-dim')
            }
          >
            {delta}
          </span>
        </div>
      )}
      {note && <div className="mt-1.5 text-[11px] text-fg-faint">{note}</div>}
    </Card>
  )
}
