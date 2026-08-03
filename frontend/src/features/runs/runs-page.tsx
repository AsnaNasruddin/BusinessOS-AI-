import { Badge } from '@/components/ui/badge'
import { statusVariant } from '@/lib/status-variant'
import { Card } from '@/components/ui/card'
import { useRun, useRunSteps } from '@/hooks/use-runs'
import { RunTimeline } from '@/features/runs/run-timeline'

const FEATURED_RUN_ID = 'run_4128'

export function RunsPage() {
  const { data: run } = useRun(FEATURED_RUN_ID)
  const { data: steps } = useRunSteps(FEATURED_RUN_ID)

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-[22px]">Runs</h1>
        <div className="mt-1 text-[13px] text-fg-dim">Every step, timed and logged.</div>
      </div>

      {run && (
        <Card className="mb-4 flex flex-wrap items-center justify-between gap-4 p-[18px]">
          <div className="flex items-center gap-3.5">
            <div>
              <div className="text-[15px] font-semibold">{run.workflowName}</div>
              <div className="font-mono text-xs text-fg-faint">{run.id}</div>
            </div>
            <Badge variant={statusVariant(run.status)}>{run.status.replace('_', ' ')}</Badge>
          </div>
          <div className="flex gap-5">
            <Stat label="Duration" value={run.durationLabel} />
            <Stat label="Tokens" value={run.totalTokens.toLocaleString()} />
            <Stat label="Cost" value={`$${run.totalCostUsd.toFixed(2)}`} />
            <Stat label="Started" value={run.startedAtLabel} />
          </div>
        </Card>
      )}

      {steps && (
        <Card className="px-5 py-2">
          <RunTimeline steps={steps} />
        </Card>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mb-0.5 text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
        {label}
      </div>
      <div className="font-mono text-sm font-semibold">{value}</div>
    </div>
  )
}
