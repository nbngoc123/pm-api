import { cva, type VariantProps } from 'class-variance-authority'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'
import { Tooltip } from './tooltip'

const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md font-medium whitespace-nowrap transition-colors aria-disabled:cursor-not-allowed aria-disabled:opacity-45 [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-white hover:bg-primary-hover aria-disabled:hover:bg-primary',
        secondary: 'border border-border-strong bg-surface text-fg hover:bg-surface-2 aria-disabled:hover:bg-surface',
        ghost: 'text-muted hover:bg-surface-2 hover:text-fg aria-disabled:hover:bg-transparent',
        danger: 'border border-border-strong bg-surface text-danger hover:bg-danger-soft',
      },
      size: {
        sm: 'h-7 px-2 text-xs',
        md: 'h-8 px-3 text-sm',
        icon: 'size-8',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean
  /**
   * Lý do nút không dùng được. Khi có giá trị, nút hiện mờ kèm tooltip giải thích
   * thay vì dùng thuộc tính disabled (vốn không hiện được tooltip).
   */
  disabledReason?: string | null
}

export function Button({ className, variant, size, loading, disabledReason, disabled, onClick, children, type = 'button', ...props }: ButtonProps) {
  const blocked = !!disabledReason || disabled || loading
  const button = (
    <button
      type={type}
      aria-disabled={blocked || undefined}
      className={cn(buttonVariants({ variant, size }), className)}
      onClick={blocked ? (e) => e.preventDefault() : onClick}
      {...props}
    >
      {children}
    </button>
  )
  return disabledReason ? <Tooltip content={disabledReason}>{button}</Tooltip> : button
}
