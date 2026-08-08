import type { Edge } from '@xyflow/react'
import type { FlowNode } from '@/features/workflow-builder/initial-graph'
import type { WorkflowNodeKind } from '@/types'

function reactFlowType(kind: WorkflowNodeKind): 'circle' | 'condition' | 'rect' {
  if (kind === 'condition') return 'condition'
  if (kind === 'trigger' || kind === 'end') return 'circle'
  return 'rect'
}

interface RawNode {
  id: string
  type: WorkflowNodeKind
  position: { x: number; y: number }
  data: Record<string, unknown>
}

interface RawEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
}

/** Converts a real, backend-compiled `Workflow.graph` (app.workflows.graph
 * shape) into React Flow's node/edge shape — same conversion the Workflow
 * Builder's mock example (initial-graph.ts) is hand-authored in already.
 * Deliberately simple: every non-condition node uses the single default
 * 'in'/'out' handle (no per-branch handle spreading like the hand-tuned
 * mock has), so a parallel/merge node's multiple edges visually converge
 * on one point rather than fanning out — real data, modest polish. */
export function graphToFlow(graph: { nodes: unknown[]; edges: unknown[] }): {
  nodes: FlowNode[]
  edges: Edge[]
} {
  const rawNodes = graph.nodes as RawNode[]
  const rawEdges = graph.edges as RawEdge[]

  const nodes: FlowNode[] = rawNodes.map((n) => ({
    id: n.id,
    type: reactFlowType(n.type),
    position: n.position,
    data: {
      ...n.data,
      label: String(n.data.label ?? n.id),
      sub: String(n.data.sub ?? n.type),
      kind: n.type,
    },
  }))

  const edges: Edge[] = rawEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle ?? 'out',
    targetHandle: 'in',
    label: e.sourceHandle,
  }))

  return { nodes, edges }
}
