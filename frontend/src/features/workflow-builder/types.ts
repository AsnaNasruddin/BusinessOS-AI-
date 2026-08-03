import type { WorkflowNodeKind } from '@/types'

export interface WorkflowNodeData extends Record<string, unknown> {
  label: string
  sub: string
  kind: WorkflowNodeKind
}
