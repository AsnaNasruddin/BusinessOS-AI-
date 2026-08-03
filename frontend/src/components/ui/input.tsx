import * as React from 'react'
import { cn } from '@/lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'h-9 w-full rounded-md border border-border bg-surface-2 px-3 text-[12.5px] text-fg placeholder:text-fg-faint focus-visible:bg-surface',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'
