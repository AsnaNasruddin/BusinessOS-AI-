import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  useAnswerClarifyingQuestion,
  useCompileGeneration,
  useGenerateWorkflow,
  useGenerationRequest,
} from '@/hooks/use-workflow-generation'

const KIND_LABEL: Record<string, string> = {
  trigger: 'Starts when',
  agent: 'AI step',
  tool: 'Tool',
  condition: 'Branch',
  approval: 'Human approval',
  parallel: 'Do at the same time',
  merge: 'Join back together',
  end: 'Done',
}

export function DescribeGoalPage() {
  const navigate = useNavigate()
  const [description, setDescription] = useState('')
  const [requestId, setRequestId] = useState<string | undefined>(undefined)
  const [answerDraft, setAnswerDraft] = useState('')

  const generate = useGenerateWorkflow()
  const { data: request } = useGenerationRequest(requestId)
  const answer = useAnswerClarifyingQuestion(requestId ?? '')
  const compile = useCompileGeneration(requestId ?? '')

  async function handleDescribe() {
    const created = await generate.mutateAsync(description)
    setRequestId(created.id)
  }

  async function handleAnswer() {
    if (!answerDraft.trim()) return
    await answer.mutateAsync(answerDraft.trim())
    setAnswerDraft('')
  }

  async function handleCompile() {
    const workflow = (await compile.mutateAsync()) as { id: string }
    navigate(`/workflows/${workflow.id}`)
  }

  const nextQuestion = request?.clarifyingQuestions[request.answers.length]

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-[22px]">Describe a workflow</h1>
        <div className="mt-1 text-[13px] text-fg-dim">
          Tell your AI employees what to do in plain English — no nodes, no wiring.
        </div>
      </div>

      {!request && (
        <Card className="flex flex-col gap-3.5 p-5">
          <textarea
            className="h-32 w-full resize-none rounded-md border border-border bg-surface-2 p-3 text-[13px] text-fg placeholder:text-fg-faint focus-visible:bg-surface"
            placeholder="e.g. When a customer emails a refund request, classify it, and if the refund is over $500 get a manager's approval before logging it."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="flex items-center justify-between gap-3">
            {generate.isError && (
              <span className="text-xs text-critical-text">
                Something went wrong — try again.
              </span>
            )}
            <Button
              variant="primary"
              className="ml-auto"
              disabled={!description.trim() || generate.isPending}
              onClick={handleDescribe}
            >
              {generate.isPending ? 'Starting…' : 'Describe it'}
            </Button>
          </div>
        </Card>
      )}

      {request && (request.status === 'pending' || request.status === 'planning') && (
        <Card className="flex items-center gap-3 p-5 text-[13px] text-fg-dim">
          <span className="h-2 w-2 animate-pulse rounded-full bg-signal" />
          Thinking about how to build this
          {request.round > 0 && ` (round ${request.round})`}…
        </Card>
      )}

      {request?.status === 'awaiting_answers' && nextQuestion && (
        <Card className="flex flex-col gap-3.5 p-5">
          <div className="text-[13px] font-semibold">One more thing:</div>
          <div className="text-[13px] text-fg-dim">{nextQuestion}</div>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Your answer…"
              value={answerDraft}
              onChange={(e) => setAnswerDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAnswer()}
            />
            <Button variant="primary" disabled={!answerDraft.trim() || answer.isPending} onClick={handleAnswer}>
              {answer.isPending ? '…' : 'Answer'}
            </Button>
          </div>
        </Card>
      )}

      {request?.status === 'ready' && request.plan && (
        <div className="flex flex-col gap-4">
          <Card className="flex flex-col gap-3.5 p-5">
            <div className="text-[13px] font-semibold">Here's what I'll build:</div>
            <div className="text-[13px] leading-[1.6] text-fg-dim">{request.plan.summary}</div>

            <ol className="flex flex-col gap-2 border-t border-border pt-3.5">
              {request.plan.nodes.map((node, i) => (
                <li key={node.ref} className="flex items-baseline gap-2.5 text-[12.5px]">
                  <span className="font-mono text-fg-faint">{i + 1}.</span>
                  <span className="text-fg-faint">{KIND_LABEL[node.kind] ?? node.kind}:</span>
                  <span className="font-medium">{node.label}</span>
                </li>
              ))}
            </ol>
          </Card>

          {request.missingComponents.length > 0 && (
            <Card className="flex flex-col gap-3 p-5">
              <div className="flex items-center gap-2 text-[13px] font-semibold">
                <Badge variant="warn">{request.missingComponents.length} gap(s)</Badge>
                Needs your attention before this can run
              </div>
              {request.missingComponents.map((gap, i) => (
                <div key={i} className="rounded-md border border-border bg-surface-2 p-3 text-[12.5px]">
                  <span className="font-semibold capitalize">{gap.kind.replace('_', ' ')}: </span>
                  <span className="text-fg-dim">{gap.name}</span>
                  <div className="mt-1 text-fg-faint">{gap.reason}</div>
                </div>
              ))}
              <div className="text-[12px] text-fg-faint">
                Create what's missing (e.g. on the Agents page), then click Review Workflow again.
              </div>
            </Card>
          )}

          <div className="flex items-center justify-between gap-3">
            {compile.isError && (
              <span className="text-xs text-critical-text">
                {(compile.error as Error)?.message ?? 'Could not compile — check the gaps above.'}
              </span>
            )}
            <Button variant="primary" className="ml-auto" disabled={compile.isPending} onClick={handleCompile}>
              {compile.isPending ? 'Building…' : 'Review Workflow'}
            </Button>
          </div>
        </div>
      )}

      {request?.status === 'failed' && (
        <Card className="flex flex-col gap-3 p-5">
          <div className="text-[13px] font-semibold text-critical-text">
            Something went wrong generating this workflow.
          </div>
          <div className="text-[12.5px] text-fg-dim">{request.error}</div>
          <Button
            className="self-start"
            onClick={() => {
              setRequestId(undefined)
              setDescription('')
            }}
          >
            Start over
          </Button>
        </Card>
      )}
    </div>
  )
}
