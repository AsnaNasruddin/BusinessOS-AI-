import { Handle, Position, type NodeProps } from '@xyflow/react'
import { cn } from '@/lib/utils'
import type { WorkflowNodeData } from '@/features/workflow-builder/types'
import { singleSource, singleTarget, type HandleSpec } from '@/features/workflow-builder/nodes/handle-spec'

const ACCENT: Record<string, string> = {
  agent: 'border-l-[3px] border-l-agent',
  tool: 'border-l-[3px] border-l-tool',
  approval: 'border-l-[3px] border-l-warn [border-left-style:dashed]',
}

export interface RectNodeData extends WorkflowNodeData {
  targets?: HandleSpec[]
  sources?: HandleSpec[]
}

export function RectNode({ data, selected }: NodeProps & { data: RectNodeData }) {
  const targets = data.targets ?? singleTarget
  const sources = data.sources ?? singleSource

  return (
    <div
      className={cn(
        'flex h-16 w-[170px] flex-col justify-center gap-0.5 overflow-hidden rounded-md border border-border bg-surface px-3.5 py-2 shadow-card',
        ACCENT[data.kind],
        selected && 'outline outline-2 outline-offset-1 outline-signal',
      )}
    >
      {targets.map((h) => (
        <Handle key={h.id} id={h.id} type="target" position={Position.Left} style={{ top: `${h.topPct}%` }} />
      ))}
      <span className="truncate text-[12.5px] font-semibold">{data.label}</span>
      <span className="truncate font-mono text-[10.5px] text-fg-faint">{data.sub}</span>
      {sources.map((h) => (
        <Handle key={h.id} id={h.id} type="source" position={Position.Right} style={{ top: `${h.topPct}%` }} />
      ))}
    </div>
  )
}
