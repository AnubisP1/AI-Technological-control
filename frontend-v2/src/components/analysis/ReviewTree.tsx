import { useState, type ReactNode } from 'react'
import { ChevronRight, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { KdReviewReport, MatchStatus } from '@/lib/api'

const STATUS_META: Record<MatchStatus, { label: string; icon: typeof CheckCircle2; className: string }> = {
  matched: { label: 'совпадение', icon: CheckCircle2, className: 'text-emerald-600 bg-emerald-50' },
  partial_match: { label: 'частичное совпадение', icon: AlertTriangle, className: 'text-amber-600 bg-amber-50' },
  not_found: { label: 'не найдено', icon: HelpCircle, className: 'text-red-600 bg-red-50' },
}

function StatusBadge({ status }: { status: MatchStatus }) {
  const meta = STATUS_META[status]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
        meta.className
      )}
    >
      <meta.icon className="h-3 w-3" />
      {meta.label}
    </span>
  )
}

function TreeNode({
  label,
  status,
  note,
  children,
  defaultOpen = true,
}: {
  label: string
  status?: MatchStatus
  note?: string | null
  children?: ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const hasChildren = Boolean(children)
  const borderClass =
    status === 'matched'
      ? 'border-l-emerald-400'
      : status === 'partial_match'
        ? 'border-l-amber-400'
        : status === 'not_found'
          ? 'border-l-red-400'
          : 'border-l-transparent'

  return (
    <div className={cn('border-l-2 pl-3', borderClass)}>
      <div
        role={hasChildren ? 'button' : undefined}
        tabIndex={hasChildren ? 0 : undefined}
        onClick={hasChildren ? () => setOpen((o) => !o) : undefined}
        className={cn(
          'flex flex-wrap items-center gap-2 rounded-lg px-2 py-1.5 text-sm',
          hasChildren && 'cursor-pointer select-none hover:bg-muted'
        )}
      >
        {hasChildren && (
          <ChevronRight
            className={cn('h-3.5 w-3.5 shrink-0 text-ink-dim transition-transform', open && 'rotate-90')}
          />
        )}
        <span className={cn('text-ink', !hasChildren && 'ml-[22px]')}>{label}</span>
        {status && <StatusBadge status={status} />}
      </div>
      {note && <div className="ml-[22px] pb-1 text-xs text-ink-dim">{note}</div>}
      {hasChildren && open && <div className="flex flex-col gap-0.5 pb-1">{children}</div>}
    </div>
  )
}

export function ReviewTree({ review }: { review: KdReviewReport }) {
  return (
    <div className="flex flex-col gap-1">
      {review.material_check && (
        <TreeNode
          label={`Материал: ${review.material_check.material_from_drawing || '—'}`}
          status={review.material_check.status}
          note={review.material_check.note}
        />
      )}
      {review.blank_check && (
        <TreeNode
          label={`Заготовка: ${review.blank_check.blank_from_drawing || '—'}`}
          status={review.blank_check.status}
          note={review.blank_check.note}
        />
      )}
      {review.technical_requirement_checks.length > 0 && (
        <TreeNode label="Технические требования" defaultOpen={false}>
          {review.technical_requirement_checks.map((tt) => (
            <TreeNode
              key={tt.number}
              label={`п.${tt.number}: ${tt.text}`}
              status={tt.is_recognized ? 'matched' : 'partial_match'}
              note={`категория: ${tt.category || 'не распознана'}`}
            />
          ))}
        </TreeNode>
      )}
    </div>
  )
}
