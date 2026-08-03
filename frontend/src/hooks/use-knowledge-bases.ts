import { useQuery } from '@tanstack/react-query'
import { mockFetch } from '@/lib/mock-fetch'
import { kbDocuments, knowledgeBases, sampleRetrieval } from '@/lib/seed-data'

// TODO(learning): swap for `api.get('/kbs')` once Module 6 (Knowledge Base / RAG) has a backend.
export function useKnowledgeBases() {
  return useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: () => mockFetch(knowledgeBases),
  })
}

export function useKbDocuments(kbId: string) {
  return useQuery({
    queryKey: ['knowledge-bases', kbId, 'documents'],
    queryFn: () => mockFetch(kbDocuments[kbId] ?? []),
    enabled: Boolean(kbId),
  })
}

/** Debug retrieval — `POST /kbs/{id}/query` in the real API. */
export function useRetrievalDebug(kbId: string, query: string) {
  return useQuery({
    queryKey: ['knowledge-bases', kbId, 'retrieval', query],
    queryFn: () => mockFetch(sampleRetrieval),
    enabled: Boolean(query),
  })
}
