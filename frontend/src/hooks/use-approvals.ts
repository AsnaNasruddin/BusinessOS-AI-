import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { mockFetch } from '@/lib/mock-fetch'
import { approvals, currentUser } from '@/lib/seed-data'
import type { ApprovalRequest, ApprovalStatus } from '@/types'

const APPROVALS_KEY = ['approvals'] as const

// TODO(learning): swap for `api.get('/approvals?status=pending')` once Module 9 has a backend.
export function useApprovals() {
  return useQuery({
    queryKey: APPROVALS_KEY,
    queryFn: () => mockFetch(approvals),
  })
}

interface DecideInput {
  id: string
  status: Extract<ApprovalStatus, 'approved' | 'rejected'>
}

/** POST /approvals/{id}/decide — updates the cache directly since there's no backend yet. */
export function useDecideApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, status }: DecideInput) => mockFetch({ id, status }, 400),
    onSuccess: ({ id, status }) => {
      queryClient.setQueryData<ApprovalRequest[]>(APPROVALS_KEY, (current) =>
        current?.map((a) =>
          a.id === id
            ? { ...a, status, decidedBy: currentUser.fullName, decidedAtLabel: 'just now' }
            : a,
        ),
      )
    },
  })
}
