import { Card } from '@/components/ui/card'

const PALETTE: { label: string; color: string; rounded?: boolean }[] = [
  { label: 'Trigger', color: 'bg-signal' },
  { label: 'Agent', color: 'bg-agent' },
  { label: 'Tool', color: 'bg-tool' },
  { label: 'Condition', color: 'bg-fg-faint' },
  { label: 'Approval', color: 'bg-warn' },
  { label: 'Parallel / Merge', color: 'bg-fg-faint', rounded: true },
  { label: 'End', color: 'bg-fg', rounded: true },
]

export function NodePalette() {
  return (
    <Card className="p-3.5">
      <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
        Node palette
      </h3>
      {PALETTE.map((item) => (
        <div
          key={item.label}
          className="mb-0.5 flex items-center gap-2 rounded-md border border-dashed border-transparent px-2 py-2 text-[12.5px] text-fg-dim hover:border-border hover:bg-surface-2 hover:text-fg"
        >
          <span className={`h-2.5 w-2.5 flex-none ${item.rounded ? 'rounded-full' : 'rounded-sm'} ${item.color}`} />
          {item.label}
        </div>
      ))}
    </Card>
  )
}
