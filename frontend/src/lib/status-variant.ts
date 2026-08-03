/** Run/step/document status → badge variant, shared across dashboard, runs, knowledge base, and approvals. */
export function statusVariant(status: string): 'good' | 'warn' | 'critical' | 'neutral' {
  switch (status) {
    case 'succeeded':
    case 'ready':
    case 'approved':
      return 'good'
    case 'awaiting_approval':
    case 'pending':
    case 'processing':
      return 'warn'
    case 'failed':
    case 'rejected':
      return 'critical'
    default:
      return 'neutral'
  }
}
