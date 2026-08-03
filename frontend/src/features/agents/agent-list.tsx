import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import type { Agent } from '@/types'

interface AgentListProps {
  agents: Agent[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function AgentList({ agents, selectedId, onSelect }: AgentListProps) {
  return (
    <Card className="p-2">
      {agents.map((agent) => (
        <button
          key={agent.id}
          type="button"
          onClick={() => onSelect(agent.id)}
          className={cn(
            'mb-0.5 flex w-full flex-col gap-1 rounded-md border border-transparent px-3 py-2.5 text-left',
            agent.id === selectedId
              ? 'border-agent bg-agent-bg'
              : 'hover:bg-surface-2',
          )}
        >
          <span className="truncate text-[13px] font-semibold">{agent.name}</span>
          <span className="truncate font-mono text-[11.5px] text-fg-faint">
            {agent.modelProvider} / {agent.modelName} · {agent.allowedTools.length} tools
          </span>
        </button>
      ))}
    </Card>
  )
}
