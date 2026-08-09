import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatRelativeTime } from '@/lib/format'
import type { ApprovalRequest, ApprovalStatus } from '@/types'

const APPROVALS_KEY = ['approvals'] as const

interface ApprovalRaw {
  id: string
  run_id: string
  workflow_name: string
  title: string
  requested_by: string
  status: ApprovalStatus
  payload_subject: string | null
  payload_body: string | null
  decided_by: string | null
  decided_at: string | null
}

function toApproval(raw: ApprovalRaw): ApprovalRequest {
  return {
    id: raw.id,
    runId: raw.run_id,
    workflowName: raw.workflow_name,
    title: raw.title,
    requestedBy: raw.requested_by,
    status: raw.status,
    payloadSubject: raw.payload_subject ?? undefined,
    payloadBody: raw.payload_body ?? undefined,
    decidedBy: raw.decided_by ?? undefined,
    decidedAtLabel: raw.decided_at ? formatRelativeTime(raw.decided_at) : undefined,
  }
}

export function useApprovals() {
  return useQuery({
    queryKey: APPROVALS_KEY,
    queryFn: async () => {
      const { data } = await api.get<ApprovalRaw[]>('/approvals')
      return data.map(toApproval)
    },
  })
}

interface DecideInput {
  id: string
  status: Extract<ApprovalStatus, 'approved' | 'rejected'>
  comment?: string
}

export function useDecideApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, status, comment }: DecideInput) => {
      const { data } = await api.post<ApprovalRaw>(`/approvals/${id}/decide`, { status, comment })
      return toApproval(data)
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<ApprovalRequest[]>(APPROVALS_KEY, (current) =>
        current?.map((a) => (a.id === updated.id ? updated : a)),
      )
    },
  })
}
