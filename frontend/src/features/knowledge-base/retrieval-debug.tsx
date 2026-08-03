import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { RetrievedChunk } from '@/types'

export function RetrievalDebug({ query, chunks }: { query: string; chunks: RetrievedChunk[] }) {
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
        Debug retrieval · k = 5
      </div>
      <div className="flex gap-2">
        <input
          readOnly
          value={query}
          className="h-9 flex-1 rounded-md border border-border bg-surface-2 px-3 font-mono text-[12.5px] text-fg"
        />
        <Button>Search</Button>
      </div>
      {chunks.map((chunk) => (
        <div key={`${chunk.source}-${chunk.chunkIndex}`} className="rounded-md border border-border bg-surface-2 p-3">
          <div className="mb-1.5 flex justify-between font-mono text-[11.5px] text-fg-faint">
            <span>
              {chunk.source} · chunk {chunk.chunkIndex}
            </span>
            <span className="font-semibold text-tool-text">{chunk.score.toFixed(3)}</span>
          </div>
          <div className="text-[12.5px] leading-[1.55] text-fg-dim">&ldquo;{chunk.text}&rdquo;</div>
        </div>
      ))}
    </Card>
  )
}
