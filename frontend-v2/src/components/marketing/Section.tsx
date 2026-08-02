import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function Container({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('mx-auto w-full max-w-6xl px-6', className)}>{children}</div>
}

export function Section({
  className,
  children,
  dark = false,
}: {
  className?: string
  children: ReactNode
  dark?: boolean
}) {
  return (
    <section
      className={cn('py-24', dark ? 'bg-dark text-white' : 'bg-bg text-ink', className)}
    >
      {children}
    </section>
  )
}
