import type { Edge, Node } from '@xyflow/react'
import type { HandleSpec } from '@/features/workflow-builder/nodes/handle-spec'
import type { WorkflowNodeData } from '@/features/workflow-builder/types'

export interface FlowNodeData extends WorkflowNodeData {
  targets?: HandleSpec[]
  sources?: HandleSpec[]
}

export type FlowNode = Node<FlowNodeData>

/**
 * The "Customer Support Triage" graph from the implementation plan's section-15
 * success criteria: trigger -> triage -> conditional RAG lookup -> draft reply
 * -> human approval -> parallel send + log -> end.
 */
export const initialNodes: FlowNode[] = [
  {
    id: 'trigger',
    type: 'circle',
    position: { x: 14, y: 128 },
    data: { label: 'New Email', sub: 'trigger · webhook', kind: 'trigger' },
  },
  {
    id: 'triage',
    type: 'rect',
    position: { x: 150, y: 118 },
    data: { label: 'Triage Classifier', sub: 'agent · llama3.1:8b', kind: 'agent' },
  },
  {
    id: 'cond',
    type: 'condition',
    position: { x: 361, y: 111 },
    data: { label: 'needs_kb?', sub: '', kind: 'condition' },
  },
  {
    id: 'searchkb',
    type: 'rect',
    position: { x: 480, y: 58 },
    data: { label: 'search_kb', sub: 'tool · RAG retrieval', kind: 'tool' },
  },
  {
    id: 'draft',
    type: 'rect',
    position: { x: 690, y: 118 },
    data: {
      label: 'Draft Reply Writer',
      sub: 'agent · llama3.1:8b',
      kind: 'agent',
      targets: [
        { id: 'in-kb', topPct: 28 },
        { id: 'in-no', topPct: 72 },
      ],
    },
  },
  {
    id: 'approval',
    type: 'rect',
    position: { x: 900, y: 118 },
    data: {
      label: 'Human Review',
      sub: 'approval · required',
      kind: 'approval',
      sources: [
        { id: 'out-a', topPct: 28 },
        { id: 'out-b', topPct: 72 },
      ],
    },
  },
  {
    id: 'sendemail',
    type: 'rect',
    position: { x: 1110, y: 58 },
    data: { label: 'send_email', sub: 'tool · Gmail (stub)', kind: 'tool' },
  },
  {
    id: 'logactivity',
    type: 'rect',
    position: { x: 1110, y: 190 },
    data: { label: 'log_activity', sub: 'tool · CRM write', kind: 'tool' },
  },
  {
    id: 'end',
    type: 'circle',
    position: { x: 1286, y: 132 },
    data: {
      label: 'Resolved',
      sub: 'end',
      kind: 'end',
      targets: [
        { id: 'in-a', topPct: 28 },
        { id: 'in-b', topPct: 72 },
      ],
    },
  },
]

export const initialEdges: Edge[] = [
  { id: 'e1', source: 'trigger', sourceHandle: 'out', target: 'triage', targetHandle: 'in' },
  { id: 'e2', source: 'triage', sourceHandle: 'out', target: 'cond', targetHandle: 'in' },
  { id: 'e3', source: 'cond', sourceHandle: 'yes', target: 'searchkb', targetHandle: 'in', label: 'yes' },
  { id: 'e4', source: 'cond', sourceHandle: 'no', target: 'draft', targetHandle: 'in-no', label: 'no' },
  { id: 'e5', source: 'searchkb', sourceHandle: 'out', target: 'draft', targetHandle: 'in-kb' },
  { id: 'e6', source: 'draft', sourceHandle: 'out', target: 'approval', targetHandle: 'in' },
  { id: 'e7', source: 'approval', sourceHandle: 'out-a', target: 'sendemail', targetHandle: 'in' },
  { id: 'e8', source: 'approval', sourceHandle: 'out-b', target: 'logactivity', targetHandle: 'in' },
  { id: 'e9', source: 'sendemail', sourceHandle: 'out', target: 'end', targetHandle: 'in-a' },
  { id: 'e10', source: 'logactivity', sourceHandle: 'out', target: 'end', targetHandle: 'in-b' },
]
