import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  GenerationMode,
  GenerationStatus,
  MissingComponent,
  WorkflowDiff,
  WorkflowGenerationRequest,
  WorkflowPlan,
} from '@/types'

interface WorkflowGenerationRequestRaw {
  id: string
  org_id: string
  mode: GenerationMode
  target_workflow_id: string | null
  raw_text: string
  status: GenerationStatus
  round: number
  clarifying_questions: string[] | null
  answers: string[] | null
  plan: RawPlan | null
  diff: RawDiff | null
  missing_components: MissingComponent[] | null
  error: string | null
}

interface RawPlan {
  summary: string
  nodes: {
    ref: string
    kind: WorkflowPlan['nodes'][number]['kind']
    label: string
    agent_ref?: string
    new_agent?: { name: string; description: string; system_prompt: string }
    tool_ref?: string
    kb_ref?: string
    condition_description?: string
    approval_message?: string
  }[]
  edges: { source_ref: string; target_ref: string; branch?: 'yes' | 'no' }[]
  missing_components: MissingComponent[]
  clarifying_questions: string[]
}

interface RawDiff {
  change_summary: string
  nodes_added: unknown[]
  nodes_removed: string[]
  nodes_modified: { id: string; before: Record<string, unknown>; after: Record<string, unknown> }[]
  edges_added: unknown[]
  edges_removed: string[]
}

function toPlan(raw: RawPlan): WorkflowPlan {
  return {
    summary: raw.summary,
    nodes: raw.nodes.map((n) => ({
      ref: n.ref,
      kind: n.kind,
      label: n.label,
      agentRef: n.agent_ref,
      newAgent: n.new_agent
        ? { name: n.new_agent.name, description: n.new_agent.description, systemPrompt: n.new_agent.system_prompt }
        : undefined,
      toolRef: n.tool_ref,
      kbRef: n.kb_ref,
      conditionDescription: n.condition_description,
      approvalMessage: n.approval_message,
    })),
    edges: raw.edges.map((e) => ({ sourceRef: e.source_ref, targetRef: e.target_ref, branch: e.branch })),
    missingComponents: raw.missing_components,
    clarifyingQuestions: raw.clarifying_questions,
  }
}

function toDiff(raw: RawDiff): WorkflowDiff {
  return {
    changeSummary: raw.change_summary,
    nodesAdded: raw.nodes_added,
    nodesRemoved: raw.nodes_removed,
    nodesModified: raw.nodes_modified,
    edgesAdded: raw.edges_added,
    edgesRemoved: raw.edges_removed,
  }
}

function toRequest(raw: WorkflowGenerationRequestRaw): WorkflowGenerationRequest {
  return {
    id: raw.id,
    orgId: raw.org_id,
    mode: raw.mode,
    targetWorkflowId: raw.target_workflow_id ?? undefined,
    rawText: raw.raw_text,
    status: raw.status,
    round: raw.round,
    clarifyingQuestions: raw.clarifying_questions ?? [],
    answers: raw.answers ?? [],
    plan: raw.plan ? toPlan(raw.plan) : undefined,
    diff: raw.diff ? toDiff(raw.diff) : undefined,
    missingComponents: raw.missing_components ?? [],
    error: raw.error ?? undefined,
  }
}

const REQUEST_KEY = (id: string) => ['workflow-generation', id] as const

/** Polls while the planner is actually working (`pending`/`planning`) —
 * `awaiting_answers` and terminal states are stable until the user acts. */
export function useGenerationRequest(requestId: string | undefined) {
  return useQuery({
    queryKey: REQUEST_KEY(requestId ?? ''),
    queryFn: async () => {
      const { data } = await api.get<WorkflowGenerationRequestRaw>(`/workflows/generate/${requestId}`)
      return toRequest(data)
    },
    enabled: Boolean(requestId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'planning' ? 1500 : false
    },
  })
}

export function useGenerateWorkflow() {
  return useMutation({
    mutationFn: async (description: string) => {
      const { data } = await api.post<WorkflowGenerationRequestRaw>('/workflows/generate', {
        description,
      })
      return toRequest(data)
    },
  })
}

export function useEditWorkflowWithNl() {
  return useMutation({
    mutationFn: async ({ workflowId, instruction }: { workflowId: string; instruction: string }) => {
      const { data } = await api.post<WorkflowGenerationRequestRaw>(
        `/workflows/${workflowId}/edit-with-nl`,
        { instruction },
      )
      return toRequest(data)
    },
  })
}

export function useAnswerClarifyingQuestion(requestId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (answer: string) => {
      const { data } = await api.post<WorkflowGenerationRequestRaw>(
        `/workflows/generate/${requestId}/answer`,
        { answer },
      )
      return toRequest(data)
    },
    onSuccess: (request) => queryClient.setQueryData(REQUEST_KEY(requestId), request),
  })
}

export function useCompileGeneration(requestId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/workflows/generate/${requestId}/compile`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REQUEST_KEY(requestId) })
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    },
  })
}

export function useApplyNlEdit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (requestId: string) => {
      const { data } = await api.post(`/workflows/edit-with-nl/${requestId}/apply`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }),
  })
}

export function useRejectNlEdit() {
  return useMutation({
    mutationFn: async ({ requestId, reason }: { requestId: string; reason?: string }) => {
      const { data } = await api.post<WorkflowGenerationRequestRaw>(
        `/workflows/edit-with-nl/${requestId}/reject`,
        { reason },
      )
      return toRequest(data)
    },
  })
}
