import { useQuery } from '@tanstack/react-query'
import { mockFetch } from '@/lib/mock-fetch'
import { agents, tools } from '@/lib/seed-data'

// TODO(learning): swap for `api.get('/agents')` once Module 5 (AI Agents) has a backend.
export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => mockFetch(agents),
  })
}

export function useTools() {
  return useQuery({
    queryKey: ['tools'],
    queryFn: () => mockFetch(tools),
  })
}
