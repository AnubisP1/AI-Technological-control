import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { motion } from 'framer-motion'
import { Download, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PartViewer } from '@/components/PartViewer'
import { Container } from '@/components/marketing/Section'
import { UploadPanel, type MaterialKind } from '@/components/analysis/UploadPanel'
import { ReviewTree } from '@/components/analysis/ReviewTree'
import { CardTable } from '@/components/analysis/CardTable'
import { MaterialRecommendation } from '@/components/analysis/MaterialRecommendation'
import { useWorkflow } from '@/lib/workflow'
import {
  analyzeKd,
  reviewKd,
  generateRouteCard,
  generatePrintRouteCard,
  downloadKdReviewPdf,
  type KdAnalysisResult,
  type KdReviewReport,
  type RouteCard as RouteCardType,
  type PrintRouteCardResponse,
  type MaterialRecommendationOption,
} from '@/lib/api'

function Card({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="min-w-0 rounded-2xl border border-border bg-surface p-6"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
        {action}
      </div>
      {children}
    </motion.section>
  )
}

const SEVERITY_STYLE: Record<string, string> = {
  blocking: 'border-red-200 bg-red-50 text-red-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  info: 'border-border bg-muted text-ink-dim',
}

export function AnalysisPage() {
  const navigate = useNavigate()
  const { setPendingInput } = useWorkflow()
  const [materialKind, setMaterialKind] = useState<MaterialKind>('metal')
  const [drawing, setDrawing] = useState<File | null>(null)
  const [stepModel, setStepModel] = useState<File | null>(null)
  const [partApplicationClassCode, setPartApplicationClassCode] = useState('PROPELLER')
  const [selectedOption, setSelectedOption] = useState<MaterialRecommendationOption | null>(null)

  const [analysis, setAnalysis] = useState<KdAnalysisResult | null>(null)
  const [review, setReview] = useState<KdReviewReport | null>(null)
  const [routeCard, setRouteCard] = useState<RouteCardType | null>(null)
  const [printCards, setPrintCards] = useState<PrintRouteCardResponse | null>(null)

  const canAnalyze =
    materialKind === 'metal' ? Boolean(drawing) : Boolean(stepModel) && Boolean(selectedOption)

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      setAnalysis(null)
      setReview(null)
      setRouteCard(null)
      setPrintCards(null)

      if (materialKind === 'metal') {
        if (!drawing) throw new Error('Не выбран чертёж')
        const analysisResult = await analyzeKd({ drawing, stepModel })
        setAnalysis(analysisResult)
        const reviewResult = await reviewKd({ drawing })
        setReview(reviewResult)
        const card = await generateRouteCard({ drawing })
        setRouteCard(card)
        setPendingInput({ kind: 'metal', drawing })
      } else {
        if (!stepModel || !selectedOption) throw new Error('Не выбрана модель или материал')
        const analysisResult = await analyzeKd({ stepModel })
        setAnalysis(analysisResult)
        const card = await generatePrintRouteCard({
          stepModel,
          amTechnologyCode: selectedOption.am_technology_code,
          materialGroupCode: selectedOption.material_group_code,
        })
        setPrintCards(card)
        setPendingInput({
          kind: 'plastic',
          stepModel,
          amTechnologyCode: selectedOption.am_technology_code,
          materialGroupCode: selectedOption.material_group_code,
        })
      }
    },
  })

  const pdfMutation = useMutation({
    mutationFn: async () => {
      if (!drawing) return
      const blob = await downloadKdReviewPdf({ drawing })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'kd_review_report.pdf'
      link.click()
      URL.revokeObjectURL(url)
    },
  })

  const boundingBox = analysis?.step_model?.bounding_box
  const partName =
    analysis?.drawing?.title_block?.part_name ?? routeCard?.part_name ?? printCards?.process_card.part_name

  return (
    <Container className="max-w-5xl py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Анализ детали</h1>
        <p className="mt-1 text-sm text-ink-dim">
          Загрузите чертёж и/или STEP-модель — система сверит их с базой НСИ и сформирует
          технологическую документацию.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <div className="flex flex-col gap-6">
          <UploadPanel
            materialKind={materialKind}
            onMaterialKindChange={setMaterialKind}
            drawing={drawing}
            onDrawingChange={setDrawing}
            stepModel={stepModel}
            onStepModelChange={setStepModel}
            partApplicationClassCode={partApplicationClassCode}
            onPartApplicationClassChange={setPartApplicationClassCode}
            busy={analyzeMutation.isPending}
            canAnalyze={canAnalyze}
            onAnalyze={() => analyzeMutation.mutate()}
          />

          {materialKind === 'plastic' && (
            <div className="rounded-2xl border border-border bg-surface p-6">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-ink-dim">
                Автоподбор материала
              </h2>
              <MaterialRecommendation
                partApplicationClassCode={partApplicationClassCode}
                onSelect={setSelectedOption}
              />
            </div>
          )}

          {boundingBox && (
            <div className="h-[280px]">
              <PartViewer
                partName={partName ?? undefined}
                lengthXMm={boundingBox.length_x}
                lengthYMm={boundingBox.length_y}
                lengthZMm={boundingBox.length_z}
              />
            </div>
          )}

          {analyzeMutation.isError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {(analyzeMutation.error as Error).message}
            </div>
          )}
        </div>

        <div className="flex min-w-0 flex-col gap-6">
          {analysis && (
            <Card title="Результат распознавания КД">
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                {analysis.drawing && (
                  <>
                    <dt className="text-ink-dim">Обозначение</dt>
                    <dd className="text-ink">{analysis.drawing.title_block.designation || '—'}</dd>
                    <dt className="text-ink-dim">Наименование детали</dt>
                    <dd className="text-ink">{analysis.drawing.title_block.part_name || '—'}</dd>
                    <dt className="text-ink-dim">Материал</dt>
                    <dd className="text-ink">{analysis.drawing.title_block.material || '—'}</dd>
                  </>
                )}
                {analysis.view_detection && (
                  <>
                    <dt className="text-ink-dim">Число видов на чертеже</dt>
                    <dd className="text-ink">{analysis.view_detection.view_count}</dd>
                  </>
                )}
                <dt className="text-ink-dim">Геометрия (STEP)</dt>
                <dd className="text-ink">
                  {analysis.step_model ? `${analysis.step_model.face_count} граней` : 'модель не загружена'}
                </dd>
              </dl>
            </Card>
          )}

          {review && (
            <Card
              title="Отчёт об оценке КД"
              action={
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={pdfMutation.isPending}
                  onClick={() => pdfMutation.mutate()}
                >
                  <Download className="h-3.5 w-3.5" />
                  {pdfMutation.isPending ? 'Формирование…' : 'PDF'}
                </Button>
              }
            >
              <ReviewTree review={review} />

              {review.findings.length > 0 && (
                <div className="mt-4 flex flex-col gap-2">
                  {review.findings.map((f, i) => (
                    <div
                      key={i}
                      className={`rounded-lg border px-3 py-2 text-xs ${SEVERITY_STYLE[f.severity]}`}
                    >
                      {f.message}
                    </div>
                  ))}
                </div>
              )}

              {review.summary && (
                <div className="mt-4 border-t border-border pt-4">
                  <div className="mb-1.5 flex items-center gap-2 text-xs font-medium text-ink-dim">
                    Резюме
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[10px]">
                      {review.summary.generated_by === 'llm' ? 'сгенерировано LLM' : 'шаблонный текст'}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-ink">{review.summary.text}</p>
                </div>
              )}
            </Card>
          )}

          {routeCard && (
            <Card title={`Маршрутная карта — ${routeCard.part_name || 'деталь'}`}>
              <p className="mb-3 text-xs text-ink-dim">{routeCard.gost_form}</p>
              <CardTable columns={routeCard.columns} rows={routeCard.rows} />

              {routeCard.technical_requirements.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 font-mono text-xs uppercase tracking-wider text-ink-dim">
                    Технические требования
                  </div>
                  <ul className="flex flex-col gap-1.5 text-xs text-ink">
                    {routeCard.technical_requirements.map((req, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-ink-dim">·</span>
                        {req}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {routeCard.warnings.length > 0 && (
                <div className="mt-4 flex flex-col gap-2">
                  {routeCard.warnings.map((w, i) => (
                    <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                      {w}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {printCards && (
            <Card title={`Карта техпроцесса печати — ${printCards.process_card.part_name || 'деталь'}`}>
              <CardTable columns={printCards.process_card.columns} rows={[printCards.process_card.row]} />

              {printCards.process_card.quality_standard && (
                <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl border border-border bg-muted/40 p-4 text-xs">
                  <div className="text-ink-dim">Допуск</div>
                  <div className="text-ink">{printCards.process_card.quality_standard.tolerance_mm} мм</div>
                  <div className="text-ink-dim">Мин. толщина стенки</div>
                  <div className="text-ink">{printCards.process_card.quality_standard.min_wall_thickness_mm} мм</div>
                  <div className="text-ink-dim">Ra без обработки</div>
                  <div className="text-ink">{printCards.process_card.quality_standard.roughness_ra_raw_um} мкм</div>
                  {printCards.process_card.quality_standard.roughness_ra_finished_um && (
                    <>
                      <div className="text-ink-dim">Ra после обработки</div>
                      <div className="text-ink">
                        {printCards.process_card.quality_standard.roughness_ra_finished_um} мкм
                      </div>
                    </>
                  )}
                  <div className="col-span-2 mt-1 text-[11px] text-ink-dim">
                    {printCards.process_card.quality_standard.source_note}
                  </div>
                </div>
              )}

              <h3 className="mb-2 mt-5 text-sm font-medium text-ink">Постобработка</h3>
              <CardTable
                columns={printCards.postprocessing_card.columns}
                rows={printCards.postprocessing_card.rows}
              />

              {printCards.warnings.length > 0 && (
                <div className="mt-4 flex flex-col gap-2">
                  {printCards.warnings.map((w, i) => (
                    <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                      {w}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {!analysis && !review && !routeCard && !printCards && (
            <div className="flex min-h-[300px] items-center justify-center rounded-2xl border border-dashed border-border text-sm text-ink-dim">
              Результат анализа появится здесь
            </div>
          )}

          {(routeCard || printCards) && (
            <div className="rounded-2xl border border-border bg-surface p-6">
              <p className="mb-3 text-sm text-ink-dim">
                Комплект технологической документации сформирован. Передайте его на
                согласование главному технологу.
              </p>
              <Button onClick={() => navigate('/app/production')}>
                Перейти к согласованию
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </Container>
  )
}
