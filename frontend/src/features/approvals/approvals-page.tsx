import { Badge } from '@/components/ui/badge'
import { useApprovals } from '@/hooks/use-approvals'
import { ApprovalCard } from '@/features/approvals/approval-card'

export function ApprovalsPage() {
  const { data: approvals } = useApprovals()
  const pendingCount = approvals?.filter((a) => a.status === 'pending').length ?? 0

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px]">Approvals</h1>
          <div className="mt-1 text-[13px] text-fg-dim">
            Nothing critical ships without a human in the loop.
          </div>
        </div>
        <Badge variant="warn">{pendingCount} pending</Badge>
      </div>

      <div className="flex flex-col gap-3.5">
        {approvals?.map((approval) => (
          <ApprovalCard key={approval.id} approval={approval} />
        ))}
      </div>
    </div>
  )
}
