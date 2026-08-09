import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatRelativeTime } from '@/lib/format'
import type { Workflow, WorkflowSource, WorkflowTriggerType } from '@/types'

interface WorkflowRaw {
  id: string
  org_id: string
  name: string
  description: string
  trigger_type: WorkflowTriggerType
  graph: { nodes: unknown[]; edges: unknown[] }
  is_active: boolean
  version: number
  source: WorkflowSource
  updated_at: string
}

function toWorkflow(raw: WorkflowRaw): Workflow {
  return {
    id: raw.id,
    orgId: raw.org_id,
    name: raw.name,
    description: raw.description,
    triggerType: raw.trigger_type,
    graph: raw.graph,
    isActive: raw.is_active,
    version: raw.version,
    source: raw.source,
    updatedAtLabel: formatRelativeTime(raw.updated_at),
  }
}

export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data } = await api.get<WorkflowRaw[]>('/workflows')
      return data.map(toWorkflow)
    },
  })
}

export function useWorkflow(workflowId: string) {
  return useQuery({
    queryKey: ['workflows', workflowId],
    queryFn: async () => {
      const { data } = await api.get<WorkflowRaw>(`/workflows/${workflowId}`)
      return toWorkflow(data)
    },
    enabled: Boolean(workflowId),
  })
}
