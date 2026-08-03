import { Badge } from '@/components/ui/badge'
import { statusVariant } from '@/lib/status-variant'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeadCell, TableRow } from '@/components/ui/table'
import type { KbDocument, KnowledgeBase } from '@/types'

export function DocTable({ kb, documents }: { kb: KnowledgeBase; documents: KbDocument[] }) {
  return (
    <Card>
      <div className="flex items-center justify-between px-4 pb-1 pt-3.5">
        <h2 className="text-sm font-semibold">
          {kb.name} — {kb.documentCount} documents
        </h2>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-faint">
          chunk ~500 tok · overlap 50
        </span>
      </div>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeadCell>File</TableHeadCell>
            <TableHeadCell>Type</TableHeadCell>
            <TableHeadCell>Size</TableHeadCell>
            <TableHeadCell>Status</TableHeadCell>
            <TableHeadCell>Chunks</TableHeadCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell className="max-w-0 truncate font-semibold">{doc.filename}</TableCell>
              <TableCell className="font-mono">{doc.mimeType}</TableCell>
              <TableCell className="font-mono">{doc.sizeLabel}</TableCell>
              <TableCell>
                <Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
              </TableCell>
              <TableCell className="font-mono">{doc.chunkCount ?? '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}
