import { Handle, Position, type NodeProps } from '@xyflow/react'
import { cn } from '@/lib/utils'
import type { WorkflowNodeData } from '@/features/workflow-builder/types'
import { singleSource, singleTarget, type HandleSpec } from '@/features/workflow-builder/nodes/handle-spec'

export interface CircleNodeData extends WorkflowNodeData {
  targets?: HandleSpec[]
  sources?: HandleSpec[]
}

export function CircleNode({ data, selected }: NodeProps & { data: CircleNodeData }) {
  const isTrigger = data.kind === 'trigger'
  const targets = data.targets ?? (isTrigger ? [] : singleTarget)
  const sources = data.sources ?? (isTrigger ? singleSource : [])

  return (
    <div className="flex w-28 flex-col items-center gap-1.5">
      <div
        className={cn(
          'relative grid h-11 w-11 flex-none place-items-center rounded-full border border-border bg-surface shadow-card',
          isTrigger && 'border-signal',
          selected && 'outline outline-2 outline-offset-2 outline-signal',
        )}
      >
        {targets.map((h) => (
          <Handle key={h.id} id={h.id} type="target" position={Position.Left} style={{ top: `${h.topPct}%` }} />
        ))}
        {isTrigger ? (
          <span className="h-2.5 w-2.5 rounded-full bg-signal" />
        ) : (
          <span className="h-2.5 w-2.5 rounded-full border-2 border-fg-faint" />
        )}
        {sources.map((h) => (
          <Handle key={h.id} id={h.id} type="source" position={Position.Right} style={{ top: `${h.topPct}%` }} />
        ))}
      </div>
      <div className="flex w-full flex-col items-center gap-px text-center">
        <span className="max-w-full truncate text-[12.5px] font-semibold">{data.label}</span>
        <span className="max-w-full truncate font-mono text-[10.5px] text-fg-faint">{data.sub}</span>
      </div>
    </div>
  )
}
