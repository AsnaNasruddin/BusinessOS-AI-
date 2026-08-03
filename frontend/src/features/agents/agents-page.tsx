import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useAgents } from '@/hooks/use-agents'
import { AgentList } from '@/features/agents/agent-list'
import { AgentDetail } from '@/features/agents/agent-detail'

export function AgentsPage() {
  const { data: agents } = useAgents()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const activeId = selectedId ?? agents?.[1]?.id ?? null
  const activeAgent = agents?.find((a) => a.id === activeId)

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px]">Agents</h1>
          <div className="mt-1 text-[13px] text-fg-dim">
            Configurations, not classes — a system prompt, a model, and a set of tools.
          </div>
        </div>
        <Button variant="primary">+ New agent</Button>
      </div>

      {agents && (
        <div className="grid grid-cols-[270px_minmax(0,1fr)] items-start gap-4">
          <AgentList agents={agents} selectedId={activeId} onSelect={setSelectedId} />
          {activeAgent && <AgentDetail agent={activeAgent} />}
        </div>
      )}
    </div>
  )
}
