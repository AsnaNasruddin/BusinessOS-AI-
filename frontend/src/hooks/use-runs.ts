import { useQuery } from '@tanstack/react-query'
import { mockFetch } from '@/lib/mock-fetch'
import { recentRuns, runSteps } from '@/lib/seed-data'

// TODO(learning): swap for `api.get('/runs/{id}')` once Module 4's engine writes real WorkflowRun rows.
export function useRun(runId: string) {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: () => mockFetch(recentRuns.find((r) => r.id === runId) ?? recentRuns[0]),
  })
}

export function useRunSteps(runId: string) {
  return useQuery({
    queryKey: ['runs', runId, 'steps'],
    queryFn: () => mockFetch(runSteps.filter((s) => s.runId === runId)),
  })
}
