import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useEditWorkflowWithNl } from '@/hooks/use-workflow-generation'

/** Docked in the real Workflow Builder's toolbar (real-workflow-view.tsx)
 * — §16.3 step 7. Kicks off the same generation pipeline as the create
 * flow, just in `mode: edit`; the resulting diff is reviewed by
 * NlEditDiffCard before anything touches the live workflow. */
export function NlEditBar({
  workflowId,
  onStarted,
  disabled,
}: {
  workflowId: string
  onStarted: (requestId: string) => void
  disabled?: boolean
}) {
  const [instruction, setInstruction] = useState('')
  const edit = useEditWorkflowWithNl()

  async function handleSubmit() {
    if (!instruction.trim()) return
    const request = await edit.mutateAsync({ workflowId, instruction: instruction.trim() })
    setInstruction('')
    onStarted(request.id)
  }

  return (
    <div className="flex items-center gap-2">
      <Input
        placeholder={'✨ Edit with AI — e.g. "add a step that logs every run"'}
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        disabled={disabled || edit.isPending}
        className="w-72"
      />
      <Button
        variant="primary"
        disabled={disabled || edit.isPending || !instruction.trim()}
        onClick={handleSubmit}
      >
        {edit.isPending ? '…' : 'Edit'}
      </Button>
    </div>
  )
}
