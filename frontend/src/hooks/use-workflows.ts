import { useQuery } from '@tanstack/react-query'
import { mockFetch } from '@/lib/mock-fetch'
import { workflows } from '@/lib/seed-data'

// TODO(learning): swap for `api.get('/workflows')` once Module 4 (Workflow Builder) has a backend.
export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: () => mockFetch(workflows),
  })
}
