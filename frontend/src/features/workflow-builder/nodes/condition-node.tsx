import { Handle, Position, type NodeProps } from '@xyflow/react'
import { cn } from '@/lib/utils'
import type { WorkflowNodeData } from '@/features/workflow-builder/types'

export function ConditionNode({ data, selected }: NodeProps & { data: WorkflowNodeData }) {
  return (
    <div className="relative h-[78px] w-[78px]">
      <Handle id="in" type="target" position={Position.Left} />
      <div
        className={cn(
          'absolute inset-2 rotate-45 rounded border border-border bg-surface shadow-card',
          selected && 'outline outline-2 outline-offset-1 outline-signal',
        )}
      />
      <div className="absolute inset-0 flex items-center justify-center px-1.5 text-center">
        <span className="max-w-full truncate font-mono text-[10.5px] font-semibold">{data.label}</span>
      </div>
      <Handle id="yes" type="source" position={Position.Top} />
      <Handle id="no" type="source" position={Position.Bottom} />
    </div>
  )
}
