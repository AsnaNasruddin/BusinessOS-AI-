import { Badge } from '@/components/ui/badge'
import { statusVariant } from '@/lib/status-variant'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeadCell, TableRow } from '@/components/ui/table'
import type { WorkflowRun } from '@/types'

export function RecentRunsTable({ runs }: { runs: WorkflowRun[] }) {
  return (
    <Card>
      <div className="flex items-center justify-between px-[18px] pb-1 pt-4">
        <h2 className="text-sm font-semibold">Recent runs</h2>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
          Most recent
        </span>
      </div>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeadCell>Workflow</TableHeadCell>
            <TableHeadCell>Trigger</TableHeadCell>
            <TableHeadCell>Status</TableHeadCell>
            <TableHeadCell>Duration</TableHeadCell>
            <TableHeadCell>Tokens</TableHeadCell>
            <TableHeadCell>Started</TableHeadCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {runs.map((run) => (
            <TableRow key={run.id}>
              <TableCell>
                <div className="font-semibold">{run.workflowName}</div>
                {run.errorNote && <div className="text-xs text-fg-faint">{run.errorNote}</div>}
              </TableCell>
              <TableCell className="font-mono tabular-nums">{run.triggerLabel}</TableCell>
              <TableCell>
                <Badge variant={statusVariant(run.status)}>{run.status.replace('_', ' ')}</Badge>
              </TableCell>
              <TableCell className="font-mono tabular-nums">{run.durationLabel}</TableCell>
              <TableCell className="font-mono tabular-nums">{run.totalTokens.toLocaleString()}</TableCell>
              <TableCell className="font-mono tabular-nums">{run.startedAtLabel}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}
