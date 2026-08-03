import type { ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { Chip } from '@/components/ui/chip'
import { Card } from '@/components/ui/card'

function FieldLabel({ children }: { children: ReactNode }) {
  return (
    <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
      {children}
    </div>
  )
}

function CodeBlock({ children }: { children: ReactNode }) {
  return (
    <div className="whitespace-pre-wrap rounded-md border border-border bg-surface-2 px-3 py-2.5 font-mono text-[12.5px] leading-[1.6] text-fg-dim">
      {children}
    </div>
  )
}

function KvRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-t border-border py-1.5 text-[12.5px] first:border-t-0">
      <span className="text-fg-faint">{k}</span>
      <span className="font-mono font-medium">{v}</span>
    </div>
  )
}

const CONTENT: Record<string, ReactNode> = {
  trigger: (
    <>
      <div>
        <FieldLabel>Trigger type</FieldLabel>
        <CodeBlock>webhook → POST /hooks/support-inbox</CodeBlock>
      </div>
      <div>
        <FieldLabel>Sample payload</FieldLabel>
        <CodeBlock>{`{\n  "from": "sam.rivera@customer.com",\n  "subject": "Damaged unit — order #58213",\n  "body": "..."\n}`}</CodeBlock>
      </div>
    </>
  ),
  triage: (
    <>
      <div>
        <FieldLabel>System prompt</FieldLabel>
        <CodeBlock>
          Classify the incoming email into billing_refund, technical_issue, or general_inquiry.
          Decide if knowledge-base lookup is needed. Return JSON: {'{'}category, urgency, needs_kb{'}'}.
        </CodeBlock>
      </div>
      <KvRow k="Model" v="ollama / llama3.1:8b" />
      <KvRow k="Temperature" v="0.2" />
      <KvRow k="Memory scope" v="none" />
      <div>
        <FieldLabel>Allowed tools</FieldLabel>
        <Chip>none</Chip>
      </div>
    </>
  ),
  cond: (
    <>
      <div>
        <FieldLabel>Expression</FieldLabel>
        <CodeBlock>classification.needs_kb == true</CodeBlock>
      </div>
      <p className="text-[12px] text-fg-faint">
        Evaluated with a restricted AST evaluator — comparisons and boolean ops only. Never
        Python <code className="font-mono">eval()</code>.
      </p>
    </>
  ),
  searchkb: (
    <>
      <div>
        <FieldLabel>Description</FieldLabel>
        <CodeBlock>Vector search over a knowledge base. Returns the top-k chunks by cosine similarity.</CodeBlock>
      </div>
      <KvRow k="Input schema" v="{ kb_id, query, k }" />
      <KvRow k="Category" v="retrieval" />
      <KvRow k="Knowledge base" v="Policy & Refunds" />
    </>
  ),
  draft: (
    <>
      <div>
        <FieldLabel>System prompt</FieldLabel>
        <CodeBlock>
          You are a support specialist for Acme Robotics. Use retrieved knowledge-base context, if
          any, to write a warm, precise reply. Never promise refunds outside policy. Return JSON:
          {'{'}subject, body, confidence{'}'}.
        </CodeBlock>
      </div>
      <KvRow k="Model" v="ollama / llama3.1:8b" />
      <KvRow k="Temperature" v="0.4" />
      <KvRow k="Memory scope" v="session" />
      <div>
        <FieldLabel>Allowed tools</FieldLabel>
        <div className="flex flex-wrap gap-1.5">
          <Chip>search_kb</Chip>
          <Chip>send_email</Chip>
        </div>
      </div>
    </>
  ),
  approval: (
    <>
      <div>
        <FieldLabel>Message template</FieldLabel>
        <CodeBlock>{`A drafted reply is ready for {{customer_name}}. Review the message below before it sends.`}</CodeBlock>
      </div>
      <KvRow k="On pause" v="awaiting_approval" />
      <KvRow k="Resumes on" v="approval webhook" />
    </>
  ),
  sendemail: (
    <>
      <div>
        <FieldLabel>Description</FieldLabel>
        <CodeBlock>Sends the approved reply. Stubbed in dev — writes to the log instead of a live provider.</CodeBlock>
      </div>
      <KvRow k="Category" v="communication" />
      <KvRow k="Config" v="Gmail OAuth (not connected)" />
    </>
  ),
  logactivity: (
    <>
      <div>
        <FieldLabel>Description</FieldLabel>
        <CodeBlock>Writes a record of the interaction to the CRM for reporting.</CodeBlock>
      </div>
      <KvRow k="Category" v="data" />
    </>
  ),
  end: (
    <p className="text-[12px] text-fg-faint">Workflow complete. No further nodes execute.</p>
  ),
}

const TYPE_LABEL: Record<string, { text: string; variant: 'neutral' | 'agent' | 'tool' | 'warn' }> = {
  trigger: { text: 'Trigger', variant: 'neutral' },
  triage: { text: 'Agent', variant: 'agent' },
  cond: { text: 'Condition', variant: 'neutral' },
  searchkb: { text: 'Tool', variant: 'tool' },
  draft: { text: 'Agent', variant: 'agent' },
  approval: { text: 'Approval', variant: 'warn' },
  sendemail: { text: 'Tool', variant: 'tool' },
  logactivity: { text: 'Tool', variant: 'tool' },
  end: { text: 'End', variant: 'neutral' },
}

const NAME: Record<string, string> = {
  trigger: 'New Email',
  triage: 'Triage Classifier',
  cond: 'needs_kb?',
  searchkb: 'search_kb',
  draft: 'Draft Reply Writer',
  approval: 'Human Review',
  sendemail: 'send_email',
  logactivity: 'log_activity',
  end: 'Resolved',
}

export function InspectorPanel({ nodeId }: { nodeId: string | null }) {
  if (!nodeId || !CONTENT[nodeId]) {
    return (
      <Card className="p-3.5 text-[13px] text-fg-dim">Select a node to inspect it.</Card>
    )
  }

  const type = TYPE_LABEL[nodeId]

  return (
    <Card className="flex flex-col gap-3.5 p-3.5">
      <div className="flex items-center justify-between">
        <Badge variant={type.variant}>{type.text}</Badge>
      </div>
      <div className="text-[15px] font-semibold">{NAME[nodeId]}</div>
      {CONTENT[nodeId]}
    </Card>
  )
}
