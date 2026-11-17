import type { ReactNode } from 'react'
import type { Tone } from '@/lib/labels'
import { cn } from '@/lib/utils'

const tones: Record<Tone, string> = {
  neutral: 'bg-neutral-soft text-neutral-soft-fg',
  primary: 'bg-primary-soft text-primary-soft-fg',
  success: 'bg-success-soft text-success-soft-fg',
  warning: 'bg-warning-soft text-warning-soft-fg',
  danger: 'bg-danger-soft text-danger-soft-fg',
  purple: 'bg-purple-soft text-purple-soft-fg',
}

export function Badge({ tone = 'neutral', className, children }: { tone?: Tone; className?: string; children: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded px-1.5 py-px text-xs font-medium whitespace-nowrap', tones[tone], className)}>
      {children}
    </span>
  )
}
