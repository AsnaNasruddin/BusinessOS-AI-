import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-[13px] font-medium transition-colors disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'border border-border bg-surface text-fg hover:bg-surface-2',
        primary:
          'border border-signal-solid bg-signal-solid text-white hover:border-signal-solid-hover hover:bg-signal-solid-hover',
        outlineCritical:
          'border border-critical bg-transparent text-critical-text hover:bg-critical-bg',
        ghost: 'border border-transparent bg-transparent text-fg-dim hover:bg-surface-2',
      },
      size: {
        default: 'h-8 px-3.5',
        sm: 'h-7 px-2.5',
        icon: 'h-8 w-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
