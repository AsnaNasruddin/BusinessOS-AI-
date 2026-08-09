import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { statusVariant } from '@/lib/status-variant'
import { Card } from '@/components/ui/card'
import { useRun, useRunSteps, useRuns } from '@/hooks/use-runs'
import { RunTimeline } from '@/features/runs/run-timeline'
import type { WorkflowRun } from '@/types'

export function RunsPage() {
  const { data: runs, isLoading } = useRuns()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const activeId = selectedId ?? runs?.[0]?.id ?? null
  const { data: run } = useRun(activeId ?? '')
  const { data: steps } = useRunSteps(activeId ?? '')

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-[22px]">Runs</h1>
        <div className="mt-1 text-[13px] text-fg-dim">Every step, timed and logged.</div>
      </div>

      {!isLoading && runs?.length === 0 && (
        <Card className="p-6 text-center text-[13px] text-fg-dim">
          No runs yet — trigger a workflow to see it here.
        </Card>
      )}

      {runs && runs.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
          <Card className="flex flex-col gap-1 p-2">
            {runs.map((r) => (
              <RunListItem
                key={r.id}
                run={r}
                active={r.id === activeId}
                onClick={() => setSelectedId(r.id)}
              />
            ))}
          </Card>

          <div>
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
                {run.errorNote && (
                  <div className="w-full text-[12.5px] text-critical-text">{run.errorNote}</div>
                )}
              </Card>
            )}

            {steps && (
              <Card className="px-5 py-2">
                <RunTimeline steps={steps} />
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function RunListItem({
  run,
  active,
  onClick,
}: {
  run: WorkflowRun
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col gap-1 rounded-md px-3 py-2.5 text-left transition-colors ${
        active ? 'bg-surface-2' : 'hover:bg-surface-2'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[13px] font-semibold">{run.workflowName}</span>
        <Badge variant={statusVariant(run.status)}>{run.status.replace('_', ' ')}</Badge>
      </div>
      <div className="flex items-center justify-between gap-2 text-[11.5px] text-fg-faint">
        <span>{run.startedAtLabel}</span>
        <span className="font-mono">{run.totalTokens.toLocaleString()} tok</span>
      </div>
    </button>
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
