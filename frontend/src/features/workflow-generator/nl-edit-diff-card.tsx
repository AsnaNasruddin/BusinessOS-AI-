import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  useApplyNlEdit,
  useGenerationRequest,
  useRejectNlEdit,
} from '@/hooks/use-workflow-generation'

/** §16.11 — the diff a natural-language edit produces, reviewed before
 * anything touches the live workflow. Polls the same generation request
 * the create flow does; once it lands on `ready` there's a `diff` to
 * show. */
export function NlEditDiffCard({
  requestId,
  onResolved,
}: {
  requestId: string
  onResolved: () => void
}) {
  const { data: request } = useGenerationRequest(requestId)
  const apply = useApplyNlEdit()
  const reject = useRejectNlEdit()

  if (!request || request.status === 'pending' || request.status === 'planning') {
    return (
      <Card className="flex items-center gap-3 p-4 text-[13px] text-fg-dim">
        <span className="h-2 w-2 animate-pulse rounded-full bg-signal" />
        Figuring out the change…
      </Card>
    )
  }

  if (request.status === 'failed') {
    return (
      <Card className="flex flex-col gap-2 p-4">
        <div className="text-[13px] font-semibold text-critical-text">Couldn't work out that edit.</div>
        <div className="text-[12.5px] text-fg-dim">{request.error}</div>
        <Button className="self-start" onClick={onResolved}>
          Dismiss
        </Button>
      </Card>
    )
  }

  if (!request.diff) {
    return null
  }

  const diff = request.diff
  const hasChanges =
    diff.nodesAdded.length + diff.nodesRemoved.length + diff.nodesModified.length > 0

  async function handleApply() {
    await apply.mutateAsync(requestId)
    onResolved()
  }

  async function handleReject() {
    await reject.mutateAsync({ requestId })
    onResolved()
  }

  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="text-[13px] font-semibold">{diff.changeSummary}</div>

      {!hasChanges && (
        <div className="text-[12.5px] text-fg-faint">No structural changes detected.</div>
      )}

      {diff.nodesAdded.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-[12.5px]">
          <Badge variant="good">+{diff.nodesAdded.length}</Badge>
          {diff.nodesAdded.map((n, i) => (
            <span key={i} className="text-fg-dim">
              {String((n as { data?: { label?: string } }).data?.label ?? 'step')}
            </span>
          ))}
        </div>
      )}

      {diff.nodesRemoved.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-[12.5px]">
          <Badge variant="critical">−{diff.nodesRemoved.length}</Badge>
          <span className="text-fg-dim">{diff.nodesRemoved.length} step(s) removed</span>
        </div>
      )}

      {diff.nodesModified.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-[12.5px]">
          <Badge variant="warn">~{diff.nodesModified.length}</Badge>
          <span className="text-fg-dim">{diff.nodesModified.length} step(s) changed</span>
        </div>
      )}

      <div className="flex items-center gap-2 border-t border-border pt-3">
        <Button variant="primary" disabled={apply.isPending} onClick={handleApply}>
          {apply.isPending ? 'Applying…' : 'Apply'}
        </Button>
        <Button variant="outlineCritical" disabled={reject.isPending} onClick={handleReject}>
          Reject
        </Button>
      </div>
    </Card>
  )
}
