import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useKbDocuments, useKnowledgeBases, useRetrievalDebug } from '@/hooks/use-knowledge-bases'
import { KbList } from '@/features/knowledge-base/kb-list'
import { DocTable } from '@/features/knowledge-base/doc-table'
import { RetrievalDebug } from '@/features/knowledge-base/retrieval-debug'

const SAMPLE_QUERY = 'damaged item refund window'

export function KnowledgeBasePage() {
  const { data: kbs } = useKnowledgeBases()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const activeId = selectedId ?? kbs?.find((k) => k.id === 'kb_policy')?.id ?? kbs?.[0]?.id ?? null
  const activeKb = kbs?.find((k) => k.id === activeId)

  const { data: documents } = useKbDocuments(activeId ?? '')
  const { data: chunks } = useRetrievalDebug(activeId ?? '', SAMPLE_QUERY)

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px]">Knowledge bases</h1>
          <div className="mt-1 text-[13px] text-fg-dim">
            Documents chunked, embedded, and retrieved at query time.
          </div>
        </div>
        <Button variant="primary">+ New knowledge base</Button>
      </div>

      {kbs && (
        <div className="grid grid-cols-[230px_minmax(0,1fr)] items-start gap-4">
          <KbList kbs={kbs} selectedId={activeId} onSelect={setSelectedId} />
          <div className="flex flex-col gap-4">
            <div className="rounded-md border border-dashed border-border p-5 text-center text-[12.5px] text-fg-faint">
              <strong className="font-semibold text-fg-dim">Drag files here</strong> or click to
              upload — PDF, DOCX, HTML
            </div>
            {activeKb && documents && <DocTable kb={activeKb} documents={documents} />}
            {chunks && <RetrievalDebug query={SAMPLE_QUERY} chunks={chunks} />}
          </div>
        </div>
      )}
    </div>
  )
}
