import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Dialog } from '@base-ui/react/dialog'
import { CheckCircle2, XCircle, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { decideApproval } from '@/lib/api'

/**
 * Диалог согласования комплекта технологической документации главным
 * технологом (Фаза 17, часть 5) — по запросу пользователя открывается
 * во всплывающем окне прямо на экране "Экспертиза НСИ", а не требует
 * перехода на отдельную страницу "Производство" для принятия решения.
 * После успешного согласования диалог закрывается и вызывает
 * onApproved — экран сам решает, что делать дальше (переход на
 * "Производство" с уже принятым решением).
 */

interface ApprovalDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onApproved: () => void
}

export function ApprovalDialog({ open, onOpenChange, onApproved }: ApprovalDialogProps) {
  const [rejectComment, setRejectComment] = useState('')

  const approveMutation = useMutation({
    mutationFn: () => decideApproval({ decision: 'approved' }),
    onSuccess: () => {
      onOpenChange(false)
      onApproved()
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => {
      if (!rejectComment.trim()) throw new Error('Укажите комментарий — что нужно исправить.')
      return decideApproval({ decision: 'rejected', comment: rejectComment })
    },
  })

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
        <Dialog.Popup className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,480px)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-surface p-6 shadow-2xl">
          <div className="mb-4 flex items-center justify-between gap-3">
            <Dialog.Title className="text-lg font-semibold text-ink">Согласование комплекта ТД</Dialog.Title>
            <Dialog.Close
              render={
                <button
                  aria-label="Закрыть"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-dim hover:bg-muted hover:text-ink"
                />
              }
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <p className="mb-4 text-sm text-ink-dim">
            Главный технолог подтверждает готовность комплекта технологической документации к
            запуску в производство, либо отклоняет его с комментарием для повторной генерации.
          </p>

          <Button className="w-full" disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
            <CheckCircle2 className="h-4 w-4" />
            Согласовать
          </Button>

          <div className="mt-3 flex gap-2">
            <input
              type="text"
              placeholder="Комментарий для повторной генерации"
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand"
            />
            <Button
              variant="secondary"
              disabled={rejectMutation.isPending}
              onClick={() => rejectMutation.mutate()}
            >
              <XCircle className="h-4 w-4" />
              Отклонить
            </Button>
          </div>

          {(approveMutation.isError || rejectMutation.isError) && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {((approveMutation.error ?? rejectMutation.error) as Error).message}
            </div>
          )}
          {rejectMutation.isSuccess && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              Комплект отклонён: «{rejectMutation.data.comment}». Вернитесь в «Анализ детали» для
              повторной генерации.
            </div>
          )}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
