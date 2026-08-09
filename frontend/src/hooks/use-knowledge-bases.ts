import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { DocumentStatus, KbDocument, KnowledgeBase, RetrievedChunk } from '@/types'

interface KnowledgeBaseRaw {
  id: string
  org_id: string
  name: string
  description: string
  document_count: number
}

interface KbDocumentRaw {
  id: string
  kb_id: string
  filename: string
  mime_type: string
  size_bytes: number
  status: DocumentStatus
  chunk_count: number | null
}

interface RetrievedChunkRaw {
  source: string
  chunk_index: number
  score: number
  text: string
}

function formatSizeLabel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function toKnowledgeBase(raw: KnowledgeBaseRaw): KnowledgeBase {
  return {
    id: raw.id,
    orgId: raw.org_id,
    name: raw.name,
    description: raw.description,
    documentCount: raw.document_count,
  }
}

function toKbDocument(raw: KbDocumentRaw): KbDocument {
  return {
    id: raw.id,
    kbId: raw.kb_id,
    filename: raw.filename,
    mimeType: raw.mime_type,
    sizeLabel: formatSizeLabel(raw.size_bytes),
    status: raw.status,
    chunkCount: raw.chunk_count,
  }
}

function toRetrievedChunk(raw: RetrievedChunkRaw): RetrievedChunk {
  return {
    source: raw.source,
    chunkIndex: raw.chunk_index,
    score: raw.score,
    text: raw.text,
  }
}

export function useKnowledgeBases() {
  return useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: async () => {
      const { data } = await api.get<KnowledgeBaseRaw[]>('/kbs')
      return data.map(toKnowledgeBase)
    },
  })
}

export function useKbDocuments(kbId: string) {
  return useQuery({
    queryKey: ['knowledge-bases', kbId, 'documents'],
    queryFn: async () => {
      const { data } = await api.get<KbDocumentRaw[]>(`/kbs/${kbId}/documents`)
      return data.map(toKbDocument)
    },
    enabled: Boolean(kbId),
  })
}

/** Debug retrieval — `POST /kbs/{id}/query`. */
export function useRetrievalDebug(kbId: string, query: string) {
  return useQuery({
    queryKey: ['knowledge-bases', kbId, 'retrieval', query],
    queryFn: async () => {
      const { data } = await api.post<RetrievedChunkRaw[]>(`/kbs/${kbId}/query`, { query, k: 5 })
      return data.map(toRetrievedChunk)
    },
    enabled: Boolean(kbId) && Boolean(query),
  })
}
