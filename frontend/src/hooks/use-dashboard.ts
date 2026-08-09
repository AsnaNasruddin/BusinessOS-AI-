import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatCompactNumber } from '@/lib/format'
import { useRuns } from '@/hooks/use-runs'

interface DashboardStatsRaw {
  active_workflows: number
  total_workflows: number
  runs_24h: number
  success_rate_7d: number
  tokens_30d: number
  est_cost_30d: number
  cost_note: string
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStatsRaw>('/dashboard/stats')
      return {
        activeWorkflows: data.active_workflows,
        totalWorkflows: data.total_workflows,
        runs24h: data.runs_24h,
        successRate7d: data.success_rate_7d,
        tokens30d: formatCompactNumber(data.tokens_30d),
        estCost30d: data.est_cost_30d,
        costNote: data.cost_note,
      }
    },
  })
}

/** The most recent real runs across every workflow — reuses Phase 6's
 * GET /runs (already org-wide, newest first), just sliced down to a
 * dashboard-sized handful rather than the full history the Runs page
 * shows. */
export function useRecentRuns() {
  const { data, ...rest } = useRuns()
  return { data: data?.slice(0, 8), ...rest }
}
