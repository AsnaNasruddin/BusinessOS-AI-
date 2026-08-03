import * as React from 'react'
import { cn } from '@/lib/utils'

export function Chip({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border border-border bg-surface-2 px-2.5 py-0.5 font-mono text-[11.5px] text-fg-dim',
        className,
      )}
      {...props}
    />
  )
}
