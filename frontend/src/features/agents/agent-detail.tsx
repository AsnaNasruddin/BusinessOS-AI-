import type { ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Chip } from '@/components/ui/chip'
import type { Agent } from '@/types'

function FieldLabel({ children }: { children: string }) {
  return (
    <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
      {children}
    </div>
  )
}

export function AgentDetail({ agent }: { agent: Agent }) {
  return (
    <Card className="flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[15px] font-semibold">{agent.name}</div>
          <div className="mt-0.5 text-[13px] text-fg-dim">{agent.description}</div>
        </div>
        <Badge variant="good">active</Badge>
      </div>

      <div>
        <FieldLabel>System prompt</FieldLabel>
        <div className="whitespace-pre-wrap rounded-md border border-border bg-surface-2 px-3 py-2.5 font-mono text-[12.5px] leading-[1.6] text-fg-dim">
          {agent.systemPrompt}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3.5">
        <div className="min-w-0">
          <FieldLabel>Model</FieldLabel>
          <div className="truncate font-mono text-[13px] font-semibold">
            {agent.modelProvider} / {agent.modelName}
          </div>
        </div>
        <div className="min-w-0">
          <FieldLabel>Temperature</FieldLabel>
          <div className="font-mono text-[13px] font-semibold">{agent.temperature}</div>
        </div>
        <div className="min-w-0">
          <FieldLabel>Memory scope</FieldLabel>
          <div className="font-mono text-[13px] font-semibold">{agent.memoryScope}</div>
        </div>
      </div>

      <div>
        <FieldLabel>Allowed tools</FieldLabel>
        <div className="flex flex-wrap gap-1.5">
          {agent.allowedTools.length > 0 ? (
            agent.allowedTools.map((t) => <Chip key={t}>{t}</Chip>)
          ) : (
            <Chip>none</Chip>
          )}
        </div>
      </div>

      <div>
        <FieldLabel>Test agent</FieldLabel>
        <div className="flex flex-col gap-2">
          <TraceRow tag="input" tone="neutral">
            "Customer says unit arrived cracked, wants a refund."
          </TraceRow>
          <TraceRow tag="agent" tone="agent">
            calls <code className="rounded bg-surface-2 px-1 font-mono text-[11.5px]">search_kb</code> with
            query <code className="rounded bg-surface-2 px-1 font-mono text-[11.5px]">"damaged item refund window"</code>
          </TraceRow>
          <TraceRow tag="tool" tone="tool">
            3 chunks returned from Policy &amp; Refunds
          </TraceRow>
          <TraceRow tag="output" tone="agent">
            <code className="rounded bg-surface-2 px-1 font-mono text-[11.5px]">
              {'{"subject":"Re: Damaged unit — order #58213","confidence":0.93}'}
            </code>
          </TraceRow>
        </div>
      </div>
    </Card>
  )
}

function TraceRow({
  tag,
  tone,
  children,
}: {
  tag: string
  tone: 'neutral' | 'agent' | 'tool'
  children: ReactNode
}) {
  const toneClass =
    tone === 'agent' ? 'bg-agent-bg text-agent-text' : tone === 'tool' ? 'bg-tool-bg text-tool-text' : 'bg-surface-3 text-fg-dim'
  return (
    <div className="flex items-start gap-2.5 text-[12.5px]">
      <span
        className={`mt-px flex-none rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide ${toneClass}`}
      >
        {tag}
      </span>
      <span className="text-fg-dim">{children}</span>
    </div>
  )
}
