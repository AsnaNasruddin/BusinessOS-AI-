import type { WorkflowStep } from '@/types'

const DOT_COLOR: Record<WorkflowStep['nodeType'], string> = {
  trigger: 'bg-signal',
  agent: 'bg-agent',
  tool: 'bg-tool',
  condition: 'bg-fg-faint',
  approval: 'bg-warn',
  parallel: 'bg-fg-faint',
  merge: 'bg-fg-faint',
  end: 'bg-fg-faint',
}

export function RunTimeline({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div className="relative pl-6 before:absolute before:bottom-1.5 before:left-[9px] before:top-1.5 before:w-px before:bg-border">
      {steps.map((step) => (
        <div key={step.id} className="relative border-b border-border py-3.5 last:border-0">
          <span
            className={`absolute -left-6 top-[18px] h-[11px] w-[11px] rounded-full border-2 border-surface shadow-[0_0_0_1px_var(--border)] ${DOT_COLOR[step.nodeType]}`}
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <span className="text-[13px] font-semibold">{step.label}</span>
              <span className="ml-2 font-mono text-[11.5px] text-fg-faint">{step.sub}</span>
            </div>
            <div className="flex gap-3.5 font-mono text-xs text-fg-dim">
              <span>{step.latencyLabel}</span>
              {step.tokensUsed !== undefined && <span>{step.tokensUsed} tok</span>}
            </div>
          </div>
          {step.payload !== undefined && (
            <details className="mt-1.5 text-xs text-fg-faint">
              <summary className="cursor-pointer select-none">payload</summary>
              <pre className="mt-2 overflow-x-auto rounded-md border border-border bg-surface-2 px-3 py-2.5 font-mono text-[11.5px] leading-[1.6] text-fg-dim">
                {JSON.stringify(step.payload, null, 2)}
              </pre>
            </details>
          )}
          {step.note && <div className="mt-1 text-[11.5px] italic text-fg-faint">{step.note}</div>}
        </div>
      ))}
    </div>
  )
}
