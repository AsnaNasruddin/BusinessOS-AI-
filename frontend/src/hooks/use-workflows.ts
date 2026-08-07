import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatRelativeTime } from '@/lib/format'
import type { Workflow, WorkflowTriggerType } from '@/types'

interface WorkflowRaw {
  id: string
  org_id: string
  name: string
  description: string
  trigger_type: WorkflowTriggerType
  is_active: boolean
  version: number
  updated_at: string
}

function toWorkflow(raw: WorkflowRaw): Workflow {
  return {
    id: raw.id,
    orgId: raw.org_id,
    name: raw.name,
    description: raw.description,
    triggerType: raw.trigger_type,
    isActive: raw.is_active,
    version: raw.version,
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
