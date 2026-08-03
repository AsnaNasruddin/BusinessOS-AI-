import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { statusVariant } from '@/lib/status-variant'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useDecideApproval } from '@/hooks/use-approvals'
import type { ApprovalRequest } from '@/types'

export function ApprovalCard({ approval }: { approval: ApprovalRequest }) {
  const [comment, setComment] = useState('')
  const decide = useDecideApproval()
  const isPending = approval.status === 'pending'

  return (
    <Card className="flex flex-col gap-3.5 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold">{approval.title}</div>
          <div className="mt-0.5 text-xs text-fg-faint">
            Requested by <strong className="font-semibold text-fg-dim">{approval.requestedBy}</strong> ·{' '}
            {approval.runId} · {approval.workflowName}
          </div>
        </div>
        <Badge variant={statusVariant(approval.status)}>{approval.status}</Badge>
      </div>

      {approval.payloadSubject && (
        <div className="rounded-md border border-border bg-surface-2 p-4">
          <div className="mb-1.5 text-[13px] font-semibold">{approval.payloadSubject}</div>
          <div className="whitespace-pre-wrap text-[13px] leading-[1.6] text-fg-dim">
            {approval.payloadBody}
          </div>
        </div>
      )}

      {isPending ? (
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            disabled={decide.isPending}
            onClick={() => decide.mutate({ id: approval.id, status: 'approved' })}
          >
            Approve
          </Button>
          <Button
            variant="outlineCritical"
            disabled={decide.isPending}
            onClick={() => decide.mutate({ id: approval.id, status: 'rejected' })}
          >
            Reject
          </Button>
          <Input
            placeholder="Add a comment (optional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
      ) : (
        <div className="text-xs text-fg-faint">
          {approval.status === 'approved' ? 'Approved' : 'Rejected'} by {approval.decidedBy} ·{' '}
          {approval.decidedAtLabel}
        </div>
      )}
    </Card>
  )
}
