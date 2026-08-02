import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ScanLine, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/marketing/Section'
import { PhotoDropzone } from '@/components/quality/PhotoDropzone'
import { ScanOverlay } from '@/components/quality/ScanOverlay'
import { useWorkflow } from '@/lib/workflow'
import { assessQualityMetal, assessQualityPrint, type QualityReport } from '@/lib/api'

const VERDICT_META: Record<
  QualityReport['verdict'],
  { label: string; icon: typeof CheckCircle2; className: string }
> = {
  ok: { label: 'норма', icon: CheckCircle2, className: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
  defective: { label: 'брак', icon: AlertTriangle, className: 'text-red-600 bg-red-50 border-red-200' },
  inconclusive: { label: 'неопределённо', icon: HelpCircle, className: 'text-amber-600 bg-amber-50 border-amber-200' },
}

// Минимальная длительность симулированного сканирования — реальное
// сравнение (OpenCV IoU) занимает доли секунды, но пользователь должен
// увидеть сам процесс, а не мгновенную подмену результата.
const MIN_SCAN_MS = 1600

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function QualityPage() {
  const { pendingInput } = useWorkflow()
  const [actualPhoto, setActualPhoto] = useState<File | null>(null)
  const [referencePhoto, setReferencePhoto] = useState<File | null>(null)

  const assessMutation = useMutation({
    mutationFn: async (): Promise<QualityReport> => {
      if (!pendingInput) throw new Error('Нет входных данных — сначала пройдите «Анализ детали».')
      if (!actualPhoto || !referencePhoto) throw new Error('Загрузите оба изображения.')

      const [report] = await Promise.all([
        pendingInput.kind === 'metal'
          ? assessQualityMetal({ drawing: pendingInput.drawing, referencePhoto, actualPhoto })
          : assessQualityPrint({
              stepModel: pendingInput.stepModel,
              referencePhoto,
              actualPhoto,
              amTechnologyCode: pendingInput.amTechnologyCode,
              materialGroupCode: pendingInput.materialGroupCode,
            }),
        delay(MIN_SCAN_MS),
      ])
      return report
    },
  })

  const report = assessMutation.data
  const canScan = Boolean(actualPhoto && referencePhoto && pendingInput)

  return (
    <Container className="max-w-4xl py-10">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">Контроль качества</h1>
      <p className="mb-8 text-sm text-ink-dim">
        Сравнение фото изготовленной детали с эталоном (фото качественного изделия, рендер или
        снимок модели) — по силуэту, не по точным геометрическим размерам.
      </p>

      {!pendingInput && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Сначала пройдите «Анализ детали» и «Производство».
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="relative">
          <PhotoDropzone label="Загруженное фото детали" file={actualPhoto} onChange={setActualPhoto} />
          <ScanOverlay active={assessMutation.isPending} />
        </div>
        <div className="relative">
          <PhotoDropzone
            label="Эталон (фото / рендер / снимок модели)"
            file={referencePhoto}
            onChange={setReferencePhoto}
          />
          <ScanOverlay active={assessMutation.isPending} />
        </div>
      </div>

      <Button
        className="mt-5 h-11 w-full text-sm"
        disabled={!canScan || assessMutation.isPending}
        onClick={() => assessMutation.mutate()}
      >
        <ScanLine className="h-4 w-4" />
        {assessMutation.isPending ? 'Сканирование…' : 'Сканировать'}
      </Button>

      {assessMutation.isError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {(assessMutation.error as Error).message}
        </div>
      )}

      {report && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="mt-8 flex flex-col gap-6"
        >
          {/* Отчёт об оценке качества */}
          <section className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-4 text-lg font-semibold tracking-tight text-ink">Отчёт об оценке качества</h2>
            <div className="flex items-center gap-3">
              {(() => {
                const meta = VERDICT_META[report.verdict]
                return (
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${meta.className}`}
                  >
                    <meta.icon className="h-4 w-4" />
                    {meta.label}
                  </span>
                )
              })()}
              <span className="font-mono text-sm text-ink-dim">
                схожесть силуэта: {Math.round(report.similarity_score * 100)}%
              </span>
            </div>
            {report.notes.length > 0 && (
              <ul className="mt-4 flex flex-col gap-2">
                {report.notes.map((note, i) => (
                  <li
                    key={i}
                    className={
                      'rounded-lg border px-3 py-2 text-xs ' +
                      (report.verdict === 'defective'
                        ? 'border-red-200 bg-red-50 text-red-700'
                        : 'border-border bg-muted/50 text-ink-dim')
                    }
                  >
                    {note}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Документы для запуска в серию — комплект ТД с расчётом ресурсов/времени */}
          {report.verdict === 'ok' && report.serial_production_plan && (
            <section className="rounded-2xl border border-border bg-surface p-6">
              <h2 className="mb-1 text-lg font-semibold tracking-tight text-ink">
                Документы для запуска в серию
              </h2>
              {report.serial_production_plan.is_demonstration_estimate && (
                <p className="mb-4 text-xs text-ink-dim">
                  Демонстрационная оценка (не производственный расчёт по режимам резания/печати).
                </p>
              )}
              <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <dt className="text-ink-dim">Число операций</dt>
                <dd className="text-ink">{report.serial_production_plan.operation_count}</dd>
                <dt className="text-ink-dim">Расчётное время цикла</dt>
                <dd className="text-ink">{report.serial_production_plan.estimated_cycle_time_minutes} мин</dd>
                <dt className="text-ink-dim">Партия 100 шт. (оценка)</dt>
                <dd className="text-ink">
                  {report.serial_production_plan.estimated_batch_100_duration_days} дн.
                </dd>
                <dt className="text-ink-dim">Себестоимость единицы (оценка)</dt>
                <dd className="text-ink">{report.serial_production_plan.estimated_unit_cost_rub} ₽</dd>
                <dt className="text-ink-dim">Уровень риска</dt>
                <dd className="text-ink">{report.serial_production_plan.risk_level}</dd>
                <dt className="text-ink-dim">Оценка процента брака</dt>
                <dd className="text-ink">{report.serial_production_plan.estimated_defect_rate_percent}%</dd>
              </dl>

              {report.serial_production_plan.workshop_load_notes.length > 0 && (
                <ul className="mt-4 flex flex-col gap-1.5 text-xs text-ink-dim">
                  {report.serial_production_plan.workshop_load_notes.map((n, i) => (
                    <li key={i}>· {n}</li>
                  ))}
                </ul>
              )}

              {report.optimization_suggestions.length > 0 && (
                <>
                  <h3 className="mb-2 mt-5 text-sm font-medium text-ink">
                    Рекомендации по оптимизации техпроцесса
                  </h3>
                  <ul className="flex flex-col gap-1.5 text-xs text-ink">
                    {report.optimization_suggestions.map((s, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-ink-dim">·</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          )}

          {/* Рекомендации по устранению причин брака */}
          {report.verdict === 'defective' && report.remediation_recommendations.length > 0 && (
            <section className="rounded-2xl border border-red-200 bg-red-50 p-6">
              <h2 className="mb-4 text-lg font-semibold tracking-tight text-red-800">
                Рекомендации по устранению причин брака
              </h2>
              <ul className="flex flex-col gap-2 text-sm text-red-800">
                {report.remediation_recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <span>·</span>
                    {r}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </motion.div>
      )}
    </Container>
  )
}
