import { useQuery } from '@tanstack/react-query'
import { mockFetch } from '@/lib/mock-fetch'
import { dashboardStats, recentRuns } from '@/lib/seed-data'

// TODO(learning): swap for `api.get('/dashboard/stats')` once Module 3 (Dashboard) has a backend.
export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => mockFetch(dashboardStats),
  })
}

export function useRecentRuns() {
  return useQuery({
    queryKey: ['dashboard', 'recent-runs'],
    queryFn: () => mockFetch(recentRuns),
  })
}
