import { type LucideIcon } from 'lucide-react'
import { Construction } from 'lucide-react'
import { Container } from '@/components/marketing/Section'

export function ModulePlaceholder({
  icon: Icon,
  title,
  phase,
}: {
  icon: LucideIcon
  title: string
  phase: string
}) {
  return (
    <Container className="flex min-h-[70vh] max-w-4xl flex-col items-center justify-center gap-4 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
        <Icon className="h-6 w-6" />
      </span>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <div className="flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-ink-dim">
        <Construction className="h-3.5 w-3.5" />
        Экран будет собран в {phase} (см. dev/PLAN.md)
      </div>
    </Container>
  )
}
