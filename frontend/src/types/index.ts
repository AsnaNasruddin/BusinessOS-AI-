/**
 * Shared domain types, mirroring the backend data model (implementation plan,
 * section 6). String-literal unions instead of TS enums throughout — enums
 * aren't erasable syntax and the project avoids them for that reason.
 */

export type MembershipRole = 'owner' | 'admin' | 'member'

export type ModelProvider = 'ollama' | 'anthropic' | 'openai' | 'groq'

export type MemoryScope = 'none' | 'session' | 'persistent'

export type WorkflowNodeKind =
  | 'trigger'
  | 'agent'
  | 'tool'
  | 'condition'
  | 'approval'
  | 'parallel'
  | 'merge'
  | 'end'

export type WorkflowTriggerType = 'manual' | 'webhook' | 'schedule' | 'email'

export type RunStatus =
  | 'queued'
  | 'running'
  | 'awaiting_approval'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export type WorkflowSource = 'manual' | 'generated' | 'hybrid'

export type GenerationMode = 'create' | 'edit'

export type GenerationStatus =
  | 'pending'
  | 'planning'
  | 'awaiting_answers'
  | 'ready'
  | 'applied'
  | 'rejected'
  | 'failed'

export interface Organization {
  id: string
  name: string
  slug: string
}

export interface User {
  id: string
  email: string
  fullName: string
}

/** One row of `GET /auth/me`'s memberships array — which orgs this user
 * belongs to and their role in each, used to drive the org switcher. */
export interface Membership {
  orgId: string
  orgName: string
  orgSlug: string
  role: MembershipRole
}

export interface Agent {
  id: string
  orgId: string
  name: string
  description: string
  systemPrompt: string
  modelProvider: ModelProvider
  modelName: string
  temperature: number
  allowedTools: string[]
  memoryScope: MemoryScope
}

export interface Tool {
  id: string
  name: string
  displayName: string
  description: string
  category: string
}

export interface KnowledgeBase {
  id: string
  orgId: string
  name: string
  description: string
  documentCount: number
}

export interface KbDocument {
  id: string
  kbId: string
  filename: string
  mimeType: string
  sizeLabel: string
  status: DocumentStatus
  chunkCount: number | null
}

export interface RetrievedChunk {
  source: string
  chunkIndex: number
  score: number
  text: string
}

export interface Workflow {
  id: string
  orgId: string
  name: string
  description: string
  triggerType: WorkflowTriggerType
  // Optional because frontend/src/lib/seed-data.ts's Dashboard mock entries
  // (not yet wired to a real workflow list) predate both fields — every
  // real API response (useWorkflow/useWorkflows) always includes them.
  graph?: { nodes: unknown[]; edges: unknown[] }
  isActive: boolean
  version: number
  source?: WorkflowSource
  updatedAtLabel: string
}

export interface WorkflowPlanNode {
  ref: string
  kind: WorkflowNodeKind
  label: string
  agentRef?: string
  newAgent?: { name: string; description: string; systemPrompt: string }
  toolRef?: string
  kbRef?: string
  conditionDescription?: string
  approvalMessage?: string
}

export interface WorkflowPlanEdge {
  sourceRef: string
  targetRef: string
  branch?: 'yes' | 'no'
}

export interface MissingComponent {
  kind: 'agent' | 'tool' | 'knowledge_base'
  name: string
  reason: string
}

export interface WorkflowPlan {
  summary: string
  nodes: WorkflowPlanNode[]
  edges: WorkflowPlanEdge[]
  missingComponents: MissingComponent[]
  clarifyingQuestions: string[]
}

export interface WorkflowDiff {
  changeSummary: string
  nodesAdded: unknown[]
  nodesRemoved: string[]
  nodesModified: { id: string; before: Record<string, unknown>; after: Record<string, unknown> }[]
  edgesAdded: unknown[]
  edgesRemoved: string[]
}

export interface WorkflowGenerationRequest {
  id: string
  orgId: string
  mode: GenerationMode
  targetWorkflowId?: string
  rawText: string
  status: GenerationStatus
  round: number
  clarifyingQuestions: string[]
  answers: string[]
  plan?: WorkflowPlan
  diff?: WorkflowDiff
  missingComponents: MissingComponent[]
  error?: string
}

export interface WorkflowRun {
  id: string
  workflowId: string
  workflowName: string
  status: RunStatus
  triggerLabel: string
  durationLabel: string
  totalTokens: number
  totalCostUsd: number
  startedAtLabel: string
  errorNote?: string
}

export interface WorkflowStep {
  id: string
  runId: string
  nodeId: string
  nodeType: WorkflowNodeKind
  label: string
  sub: string
  latencyLabel: string
  tokensUsed?: number
  payload?: unknown
  note?: string
}

export interface ApprovalRequest {
  id: string
  runId: string
  workflowName: string
  title: string
  requestedBy: string
  status: ApprovalStatus
  payloadSubject?: string
  payloadBody?: string
  decidedBy?: string
  decidedAtLabel?: string
}
