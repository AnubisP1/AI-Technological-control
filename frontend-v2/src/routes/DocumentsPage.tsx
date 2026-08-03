import { useMutation } from '@tanstack/react-query'
import { FileText, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/marketing/Section'
import { useWorkflow } from '@/lib/workflow'
import {
  downloadKdReviewPdf,
  downloadRouteCardPdf,
  downloadOperationCardPdf,
  downloadPrintRouteCardPdf,
} from '@/lib/api'

/**
 * "Документы" (Фаза 17, часть 3) — центральный хаб технологической
 * документации, по идее из UI UX reference/ai_technologist_site/documents.html
 * (единая библиотека всех документов проекта). В отличие от прототипа
 * (список из 6 документов с выдуманными статусами согласования/версиями),
 * здесь показаны только те документы, что реально может сформировать
 * backend для текущей загруженной детали (pendingInput из "Анализ детали") —
 * без версий/согласований, которых система не отслеживает, и без
 * документов, которые backend не генерирует (напр. "Стоимость и риски"
 * как отдельный файл — это часть отчёта Модуля 3, не самостоятельный PDF).
 * Каждая карточка запрашивает документ заново по клику — backend не хранит
 * результаты между запросами, поэтому нет смысла кешировать факт "документ
 * уже готов" отдельно от самого файла.
 */

interface DocEntry {
  id: string
  title: string
  description: string
  format: string
  download: () => Promise<Blob>
  filename: string
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function DocCard({ doc }: { doc: DocEntry }) {
  const mutation = useMutation({
    mutationFn: async () => {
      const blob = await doc.download()
      downloadBlob(blob, doc.filename)
    },
  })

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-surface p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-brand/10 text-brand">
        <FileText className="h-4 w-4" />
      </div>
      <h3 className="mb-1 text-sm font-semibold text-ink">{doc.title}</h3>
      <p className="mb-4 flex-1 text-xs leading-relaxed text-ink-dim">{doc.description}</p>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-dim">{doc.format}</span>
        <Button size="sm" variant="secondary" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
          <Download className="h-3.5 w-3.5" />
          {mutation.isPending ? 'Формирование…' : 'Скачать'}
        </Button>
      </div>
      {mutation.isError && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[11px] text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}
    </div>
  )
}

export function DocumentsPage() {
  const { pendingInput } = useWorkflow()

  const metalDocs: DocEntry[] =
    pendingInput?.kind === 'metal'
      ? [
          {
            id: 'kd-review',
            title: 'Отчёт об оценке КД',
            description: 'Сверка материала и заготовки с БД НСИ, оценка технических требований, находки и резюме.',
            format: 'PDF',
            filename: 'kd_review_report.pdf',
            download: () => downloadKdReviewPdf({ drawing: pendingInput.drawing }),
          },
          {
            id: 'route-card',
            title: 'Маршрутная карта',
            description: 'Последовательность операций и подобранного оборудования по ГОСТ 3.1118-82.',
            format: 'PDF',
            filename: 'route_card.pdf',
            download: () => downloadRouteCardPdf({ drawing: pendingInput.drawing }),
          },
          {
            id: 'operation-card',
            title: 'Операционная карта',
            description: 'Режимы резания (t/S/V/n), оснастка и оборудование по операциям, ГОСТ 3.1404-86.',
            format: 'PDF',
            filename: 'operation_card.pdf',
            download: () => downloadOperationCardPdf({ drawing: pendingInput.drawing }),
          },
        ]
      : []

  const printDocs: DocEntry[] =
    pendingInput?.kind === 'plastic'
      ? [
          {
            id: 'print-card',
            title: 'Карта техпроцесса печати',
            description: 'Технология, принтер, материал, расчётные высота слоя/время печати/расход и карта постобработки.',
            format: 'PDF',
            filename: 'print_process_card.pdf',
            download: () =>
              downloadPrintRouteCardPdf({
                stepModel: pendingInput.stepModel,
                amTechnologyCode: pendingInput.amTechnologyCode,
                materialGroupCode: pendingInput.materialGroupCode,
              }),
          },
        ]
      : []

  const docs = [...metalDocs, ...printDocs]

  return (
    <Container className="max-w-5xl py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Документы</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-dim">
          Технологическая документация, которую система может сформировать для загруженной детали —
          каждый документ формируется заново по запросу, backend не хранит историю версий между запросами.
        </p>
      </div>

      {!pendingInput && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Деталь не загружена. Сначала пройдите «Анализ детали», затем вернитесь сюда за документами.
        </div>
      )}

      {pendingInput && docs.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {docs.map((doc) => (
            <DocCard key={doc.id} doc={doc} />
          ))}
        </div>
      )}
    </Container>
  )
}
