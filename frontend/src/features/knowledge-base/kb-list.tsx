import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import type { KnowledgeBase } from '@/types'

interface KbListProps {
  kbs: KnowledgeBase[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function KbList({ kbs, selectedId, onSelect }: KbListProps) {
  return (
    <Card className="p-2">
      {kbs.map((kb) => (
        <button
          key={kb.id}
          type="button"
          onClick={() => onSelect(kb.id)}
          className={cn(
            'mb-0.5 flex w-full flex-col gap-0.5 rounded-md border border-transparent px-3 py-2.5 text-left',
            kb.id === selectedId ? 'border-tool bg-tool-bg' : 'hover:bg-surface-2',
          )}
        >
          <span className="truncate text-[13px] font-semibold">{kb.name}</span>
          <span className="truncate text-[11.5px] text-fg-faint">{kb.documentCount} documents</span>
        </button>
      ))}
    </Card>
  )
}
