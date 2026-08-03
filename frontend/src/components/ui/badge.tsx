import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11.5px] font-semibold before:h-1.5 before:w-1.5 before:flex-none before:rounded-full before:content-['']",
  {
    variants: {
      variant: {
        good: 'bg-good-bg text-good-text before:bg-good-text',
        warn: 'bg-warn-bg text-warn-text before:bg-warn-text',
        critical: 'bg-critical-bg text-critical-text before:bg-critical-text',
        neutral: 'bg-surface-2 text-fg-dim before:bg-fg-faint',
        agent: 'bg-agent-bg text-agent-text before:bg-agent-text',
        tool: 'bg-tool-bg text-tool-text before:bg-tool-text',
      },
    },
    defaultVariants: { variant: 'neutral' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
