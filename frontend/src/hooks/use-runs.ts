import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatDuration, formatLatency, formatRelativeTime } from '@/lib/format'
import type { RunStatus, WorkflowNodeKind, WorkflowRun, WorkflowStep } from '@/types'

interface RunRaw {
  id: string
  workflow_id: string
  workflow_name: string
  status: RunStatus
  trigger_label: string
  total_tokens: number
  total_cost_usd: number
  error_note: string | null
  started_at: string
  finished_at: string | null
}

interface WorkflowStepRaw {
  id: string
  run_id: string
  node_id: string
  node_type: WorkflowNodeKind
  label: string
  sub: string
  latency_ms: number
  tokens_used: number | null
  payload: unknown
  note: string | null
}

function toRun(raw: RunRaw): WorkflowRun {
  return {
    id: raw.id,
    workflowId: raw.workflow_id,
    workflowName: raw.workflow_name,
    status: raw.status,
    triggerLabel: raw.trigger_label,
    durationLabel: formatDuration(raw.started_at, raw.finished_at),
    totalTokens: raw.total_tokens,
    totalCostUsd: raw.total_cost_usd,
    startedAtLabel: formatRelativeTime(raw.started_at),
    errorNote: raw.error_note ?? undefined,
  }
}

function toStep(raw: WorkflowStepRaw): WorkflowStep {
  return {
    id: raw.id,
    runId: raw.run_id,
    nodeId: raw.node_id,
    nodeType: raw.node_type,
    label: raw.label,
    sub: raw.sub,
    latencyLabel: formatLatency(raw.latency_ms),
    tokensUsed: raw.tokens_used ?? undefined,
    payload: raw.payload ?? undefined,
    note: raw.note ?? undefined,
  }
}

export function useRuns() {
  return useQuery({
    queryKey: ['runs'],
    queryFn: async () => {
      const { data } = await api.get<RunRaw[]>('/runs')
      return data.map(toRun)
    },
  })
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: async () => {
      const { data } = await api.get<RunRaw>(`/runs/${runId}`)
      return toRun(data)
    },
    enabled: Boolean(runId),
  })
}

export function useRunSteps(runId: string) {
  return useQuery({
    queryKey: ['runs', runId, 'steps'],
    queryFn: async () => {
      const { data } = await api.get<WorkflowStepRaw[]>(`/runs/${runId}/steps`)
      return data.map(toStep)
    },
    enabled: Boolean(runId),
  })
}
