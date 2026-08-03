import { Button } from '@/components/ui/button'
import { useDashboardStats, useRecentRuns } from '@/hooks/use-dashboard'
import { currentUser } from '@/lib/seed-data'
import { StatTile } from '@/features/dashboard/stat-tile'
import { RecentRunsTable } from '@/features/dashboard/recent-runs-table'

export function DashboardPage() {
  const { data: stats } = useDashboardStats()
  const { data: runs } = useRecentRuns()

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-5">
        <div>
          <h1 className="text-[22px]">Good afternoon, {currentUser.fullName.split(' ')[0]}.</h1>
          <div className="mt-1 text-[13px] text-fg-dim">
            Here&rsquo;s what your agents did across Acme Robotics today.
          </div>
        </div>
        <Button variant="primary">+ New workflow</Button>
      </div>

      {stats && (
        <div className="mb-[22px] grid grid-cols-2 gap-3.5 sm:grid-cols-3 lg:grid-cols-5">
          <StatTile
            label="Active workflows"
            value={`${stats.activeWorkflows} / ${stats.totalWorkflows}`}
            points={[14, 15, 13, 14, 12, 13, 12]}
            color="var(--text-faint)"
          />
          <StatTile
            label="Runs · 24h"
            value={String(stats.runs24h)}
            points={[20, 17, 18, 12, 13, 8, 6]}
            color="var(--signal)"
            delta="↑ 18% vs yesterday"
            deltaTone="up"
          />
          <StatTile
            label="Success rate · 7d"
            value={`${stats.successRate7d}%`}
            points={[10, 9, 12, 9, 7, 8, 6]}
            color="var(--good)"
            delta="↑ 1.2pt"
            deltaTone="up"
          />
          <StatTile
            label="Tokens · 30d"
            value={stats.tokens30d}
            points={[18, 16, 17, 11, 12, 9, 10]}
            color="var(--agent)"
            delta="local + cloud"
          />
          <StatTile
            label="Est. cost · 30d"
            value={`$${stats.estCost30d.toFixed(2)}`}
            points={[20, 20, 20, 17, 17, 13, 11]}
            color="var(--tool)"
            note={stats.costNote}
          />
        </div>
      )}

      {runs && <RecentRunsTable runs={runs} />}
    </div>
  )
}
