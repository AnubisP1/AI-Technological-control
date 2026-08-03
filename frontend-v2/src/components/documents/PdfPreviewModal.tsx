import { useEffect, useState } from 'react'
import { Dialog } from '@base-ui/react/dialog'
import { X, Download, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

/**
 * Предпросмотр PDF-документа в модальном окне (Фаза 17, часть 4) — по
 * запросу пользователя: клик по карточке документа должен показывать
 * сам файл, а не только скачивать его. Встраивает PDF через <embed>
 * (браузер использует собственный PDF-рендерер, тот же, что и при
 * открытии PDF в новой вкладке) — без сторонних PDF.js-зависимостей,
 * так как задача офлайн-совместимости уже решена нативным движком
 * браузера.
 */

interface PdfPreviewModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  filename: string
  load: (() => Promise<Blob>) | null
}

export function PdfPreviewModal({ open, onOpenChange, title, filename, load }: PdfPreviewModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!open || !load) return
    let cancelled = false
    let createdUrl: string | null = null

    setIsLoading(true)
    setError(null)
    setBlobUrl(null)

    load()
      .then((blob) => {
        if (cancelled) return
        createdUrl = URL.createObjectURL(blob)
        setBlobUrl(createdUrl)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [open, load])

  function handleDownload() {
    if (!blobUrl) return
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    link.click()
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
        <Dialog.Popup className="fixed left-1/2 top-1/2 z-50 flex h-[85vh] w-[min(92vw,900px)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl">
          <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-3">
            <Dialog.Title className="text-sm font-semibold text-ink">{title}</Dialog.Title>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="secondary" disabled={!blobUrl} onClick={handleDownload}>
                <Download className="h-3.5 w-3.5" />
                Скачать
              </Button>
              <Dialog.Close
                render={
                  <button
                    aria-label="Закрыть предпросмотр"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-dim hover:bg-muted hover:text-ink"
                  />
                }
              >
                <X className="h-4 w-4" />
              </Dialog.Close>
            </div>
          </div>
          <div className="flex-1 overflow-hidden bg-muted/40">
            {isLoading && (
              <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-dim">
                <Loader2 className="h-4 w-4 animate-spin" />
                Формирование документа…
              </div>
            )}
            {error && (
              <div className="flex h-full items-center justify-center px-6 text-center text-sm text-red-700">
                {error}
              </div>
            )}
            {blobUrl && !isLoading && !error && (
              <embed src={blobUrl} type="application/pdf" className="h-full w-full" />
            )}
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
