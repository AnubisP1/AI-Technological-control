import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router'
import { motion } from 'framer-motion'
import { PlayCircle, ArrowRight, ClipboardCheck, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/marketing/Section'
import { MachineIcon } from '@/components/production/MachineIcon'
import { ToolpathViewer } from '@/components/production/ToolpathViewer'
import { PageBackdrop } from '@/components/PageBackdrop'
import { useSimulationClock, operationBoundaries, TOTAL_MS } from '@/lib/useSimulationClock'
import { useWorkflow } from '@/lib/workflow'
import {
  simulatePrintManufacturing,
  generateMetalToolpath,
  type SimulationPlan,
  type ToolpathResponse,
  type ToolpathOperation,
} from '@/lib/api'

const _FEATURE_ICON: Record<ToolpathOperation['feature_kind'], string> = {
  facing: 'mill',
  pocket: 'mill',
  hole: 'drill',
}

function ProgramOutput({ lines, revealCount }: { lines: string[]; revealCount: number }) {
  if (lines.length === 0) {
    return <p className="text-sm text-ink-dim">Для этой операции управляющая программа не формируется.</p>
  }
  return (
    <pre className="max-h-56 overflow-y-auto rounded-lg bg-dark p-4 font-mono text-xs leading-relaxed text-emerald-300">
      {lines.slice(0, revealCount).map((line, i) => (
        <div key={i}>{line}</div>
      ))}
      {revealCount < lines.length && <span className="animate-pulse">▍</span>}
    </pre>
  )
}

/**
 * Реальный путь для металла (Фаза 22): вычисленный тулпас + voxel-съём
 * материала, вместо старой построчной typewriter-имитации статичного
 * шаблона. Активная операция подсвечивается по текущему шагу voxel-
 * анимации (start_step/end_step, см. routes.py::_toolpath_pipeline_result_to_dict),
 * не по отдельной шкале прогресса — один источник истины на экране.
 */
function ToolpathSimulation({ response, stepModel }: { response: ToolpathResponse; stepModel: File }) {
  const navigate = useNavigate()
  const [playing, setPlaying] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [totalSteps, setTotalSteps] = useState(0)
  const [done, setDone] = useState(false)

  const { toolpath, simulation } = response

  if (toolpath.unsupported_warning) {
    return (
      <div className="flex flex-col items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-6">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
          <AlertTriangle className="h-5 w-5" />
        </span>
        <p className="text-sm text-amber-800">{toolpath.unsupported_warning}</p>
        <p className="text-xs text-amber-700">
          Маршрутная/операционная карта остаются доступны на экране «Анализ детали» — автогенерация
          затрагивает только построение управляющей программы по геометрии.
        </p>
      </div>
    )
  }

  const activeOperation =
    toolpath.operations.find((op) => currentStep >= op.start_step && currentStep < op.end_step) ??
    toolpath.operations[toolpath.operations.length - 1]

  function handleProgress(step: number, total: number) {
    setCurrentStep(step)
    setTotalSteps(total)
    if (step >= total) setDone(true)
  }

  return (
    <div className="flex flex-col gap-5">
      {toolpath.warnings.length > 0 && (
        <div className="flex flex-col gap-2">
          {toolpath.warnings.map((w, i) => (
            <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              {w}
            </div>
          ))}
        </div>
      )}

      {simulation && (
        <div className="h-[320px]">
          <ToolpathViewer
            simulation={simulation}
            operations={toolpath.operations}
            stepModel={stepModel}
            playing={playing}
            onProgress={handleProgress}
          />
        </div>
      )}

      {!playing && (
        <Button onClick={() => setPlaying(true)}>
          <PlayCircle className="h-4 w-4" />
          Запустить расчёт и симуляцию обработки
        </Button>
      )}

      {playing && (
        <>
          <div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-brand"
                animate={{ width: totalSteps > 0 ? `${Math.round((currentStep / totalSteps) * 100)}%` : '0%' }}
                transition={{ ease: 'linear', duration: 0.1 }}
              />
            </div>
            <p className="mt-1.5 font-mono text-xs text-ink-dim">
              шаг {currentStep} из {totalSteps}
            </p>
          </div>

          {activeOperation && (
            <div className="flex items-center gap-4 rounded-xl border border-brand/20 bg-brand/[0.03] p-4">
              <span className="text-brand">
                <MachineIcon code={_FEATURE_ICON[activeOperation.feature_kind]} size={44} />
              </span>
              <div>
                <div className="font-medium text-ink">
                  {activeOperation.feature_kind === 'hole' ? 'Сверление/фрезерование отверстия' : 'Фрезерование'} —{' '}
                  {activeOperation.tool_designation}
                </div>
                <div className="text-xs text-ink-dim">
                  S{activeOperation.spindle_speed_rpm} об/мин · F{activeOperation.feed_mm_min} мм/мин ·{' '}
                  {activeOperation.estimated_time_min} мин расчётного времени
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {toolpath.operations.map((op) => (
              <div
                key={op.sequence_no}
                className={
                  'rounded-full border px-3 py-1 text-xs transition-colors ' +
                  (op === activeOperation
                    ? 'border-brand bg-brand text-white'
                    : currentStep >= op.end_step
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-border bg-surface text-ink-dim')
                }
              >
                {op.sequence_no}. {op.feature_kind === 'hole' ? 'Отверстие' : 'Фрезерование'}
              </div>
            ))}
          </div>

          {activeOperation && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-ink">Управляющая программа (реальный расчёт)</h3>
              <ProgramOutput
                lines={activeOperation.gcode_lines}
                revealCount={
                  activeOperation.end_step === activeOperation.start_step
                    ? activeOperation.gcode_lines.length
                    : Math.max(
                        1,
                        Math.round(
                          ((currentStep - activeOperation.start_step) /
                            (activeOperation.end_step - activeOperation.start_step)) *
                            activeOperation.gcode_lines.length
                        )
                      )
                }
              />
              <p className="mt-2 text-[11px] text-ink-dim">{activeOperation.source_note}</p>
            </div>
          )}

          {done && (
            <Button className="self-start" onClick={() => navigate('/app/quality')}>
              Перейти к контролю качества
              <ArrowRight className="h-4 w-4" />
            </Button>
          )}
        </>
      )}
    </div>
  )
}

/** Легаси-путь без геометрии (пластик, и запасной вариант для металла
 * без загруженного STEP) — прежняя typewriter-имитация статичного
 * шаблона program_templates.py, см. manufacturing_simulation_service.py. */
function LegacySimulation({ plan }: { plan: SimulationPlan }) {
  const navigate = useNavigate()
  const [simulationStarted, setSimulationStarted] = useState(false)
  const [simulationDone, setSimulationDone] = useState(false)

  const operations = useMemo(() => operationBoundaries(plan.operations), [plan])
  const elapsedMs = useSimulationClock(simulationStarted && !simulationDone, operations.length)

  if (simulationStarted && !simulationDone && elapsedMs >= TOTAL_MS) {
    setSimulationDone(true)
  }

  const progressPercent = Math.round((elapsedMs / TOTAL_MS) * 100)
  const currentOperationIndex = operations.findIndex((op) => elapsedMs >= op.startMs && elapsedMs < op.endMs)
  const activeIndex = simulationDone
    ? operations.length - 1
    : currentOperationIndex === -1
      ? 0
      : currentOperationIndex

  return (
    <div className="flex flex-col gap-5">
      {!simulationStarted && (
        <Button disabled={plan.operations.length === 0} onClick={() => setSimulationStarted(true)}>
          <PlayCircle className="h-4 w-4" />
          Запустить симуляцию изготовления
        </Button>
      )}

      {plan.operations.length === 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          Не удалось построить план симуляции — автоподбор техпроцесса не дал операций.
        </div>
      )}

      {simulationStarted && (
        <>
          <div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-brand"
                animate={{ width: `${progressPercent}%` }}
                transition={{ ease: 'linear', duration: 0.1 }}
              />
            </div>
            <p className="mt-1.5 font-mono text-xs text-ink-dim">
              {progressPercent}% · {(elapsedMs / 1000).toFixed(1)} с из 15 с
            </p>
          </div>

          {operations[activeIndex] && (
            <div className="flex items-center gap-4 rounded-xl border border-brand/20 bg-brand/[0.03] p-4">
              <span className="text-brand">
                <MachineIcon code={operations[activeIndex].machine_icon} size={44} />
              </span>
              <div>
                <div className="font-medium text-ink">{operations[activeIndex].name}</div>
                <div className="text-xs text-ink-dim">{operations[activeIndex].machine_label}</div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {operations.map((op, i) => (
              <div
                key={op.sequence_no}
                className={
                  'rounded-full border px-3 py-1 text-xs transition-colors ' +
                  (i === activeIndex
                    ? 'border-brand bg-brand text-white'
                    : elapsedMs >= op.endMs
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-border bg-surface text-ink-dim')
                }
              >
                {i + 1}. {op.name}
              </div>
            ))}
          </div>

          {operations[activeIndex] && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-ink">
                Управляющая программа — {operations[activeIndex].name}
              </h3>
              <ProgramOutput
                lines={operations[activeIndex].program_lines}
                revealCount={
                  operations[activeIndex].program_lines.length === 0
                    ? 0
                    : Math.max(
                        1,
                        Math.round(
                          ((elapsedMs - operations[activeIndex].startMs) /
                            (operations[activeIndex].endMs - operations[activeIndex].startMs)) *
                            operations[activeIndex].program_lines.length
                        )
                      )
                }
              />
            </div>
          )}

          {simulationDone && (
            <Button className="self-start" onClick={() => navigate('/app/quality')}>
              Перейти к контролю качества
              <ArrowRight className="h-4 w-4" />
            </Button>
          )}
        </>
      )}
    </div>
  )
}

export function ProductionPage() {
  const { pendingInput, nsiExpertiseAcknowledged, approvalApproved } = useWorkflow()
  const readyForApproval = Boolean(pendingInput) && nsiExpertiseAcknowledged

  const [toolpathResult, setToolpathResult] = useState<ToolpathResponse | null>(null)
  const [legacyPlan, setLegacyPlan] = useState<SimulationPlan | null>(null)

  // Решение о согласовании принимается в ApprovalDialog на экране
  // "Экспертиза НСИ" (Фаза 17, часть 5) — сюда попадают уже с
  // approvalApproved=true, поэтому построение результата запускается
  // сразу, без повторного запроса решения на этой странице.
  const planMutation = useMutation({
    mutationFn: async () => {
      if (!pendingInput) throw new Error('Нет входных данных — сначала пройдите «Анализ детали».')

      if (pendingInput.kind === 'metal') {
        // Фаза 23: STEP снова опционален (чертёж можно отправить на
        // проверку один). Без модели тулпас не считается вовсе — вместо
        // него ниже показывается честное сообщение, а не декоративная
        // анимация: реальной геометрии для расчёта съёма материала нет.
        if (!pendingInput.stepModel) return
        const result = await generateMetalToolpath({
          stepModel: pendingInput.stepModel,
          drawing: pendingInput.drawing,
        })
        setToolpathResult(result)
      } else {
        const simulationResult = await simulatePrintManufacturing({
          stepModel: pendingInput.stepModel,
          amTechnologyCode: pendingInput.amTechnologyCode,
          materialGroupCode: pendingInput.materialGroupCode,
        })
        setLegacyPlan(simulationResult.plan)
      }
    },
  })

  // Металл без STEP-модели: расчёт УП невозможен, запускать мутацию
  // незачем — экран сразу показывает, чего не хватает.
  const metalWithoutModel = pendingInput?.kind === 'metal' && !pendingInput.stepModel

  useEffect(() => {
    if (metalWithoutModel) return
    if (readyForApproval && approvalApproved && !toolpathResult && !legacyPlan && !planMutation.isPending) {
      planMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyForApproval, approvalApproved])

  if (!readyForApproval) {
    return (
      <Container className="max-w-2xl py-10">
        <PageBackdrop />
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">Производство</h1>
        <p className="mb-8 text-sm text-ink-dim">
          Согласование комплекта технологической документации главным технологом.
        </p>

        <div className="flex flex-col items-start gap-4 rounded-2xl border border-dashed border-border bg-surface p-6">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
            <ClipboardCheck className="h-5 w-5" />
          </span>
          {!pendingInput ? (
            <>
              <p className="text-sm text-ink">Деталь ещё не загружена.</p>
              <p className="text-xs text-ink-dim">
                Согласование доступно только после анализа детали и экспертизы соответствия НСИ.
              </p>
              <Link to="/app/analysis" className="inline-flex items-center gap-1.5 text-sm font-medium text-brand hover:underline">
                Перейти к анализу детали
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </>
          ) : (
            <>
              <p className="text-sm text-ink">Экспертиза соответствия НСИ ещё не пройдена.</p>
              <p className="text-xs text-ink-dim">
                Главный технолог согласовывает комплект технологической документации только после
                того, как деталь прошла сверку с базой НСИ.
              </p>
              <Link
                to="/app/nsi-expertise"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-brand hover:underline"
              >
                Перейти к экспертизе НСИ
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </>
          )}
        </div>
      </Container>
    )
  }

  if (approvalApproved && metalWithoutModel) {
    return (
      <Container className="max-w-2xl py-10">
        <PageBackdrop />
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">Комплект ТД согласован</h1>
        <p className="mb-8 text-sm text-ink-dim">
          Изготовление детали «{pendingInput?.kind === 'metal' ? pendingInput.routeCard.part_name ?? '—' : '—'}»
        </p>

        <div className="flex flex-col items-start gap-4 rounded-2xl border border-dashed border-border bg-surface p-6">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
            <ClipboardCheck className="h-5 w-5" />
          </span>
          <p className="text-sm text-ink">
            Расчёт управляющей программы недоступен: деталь загружена без 3D-модели.
          </p>
          <p className="text-xs leading-relaxed text-ink-dim">
            Траектория инструмента и симуляция съёма материала считаются по реальной геометрии
            детали из STEP-модели. По одному чертежу их построить нельзя, а показывать
            непосчитанную траекторию система не будет. Оценка КД, проверки оформления по ГОСТ,
            сверка с НСИ и маршрутная карта — уже сформированы и остаются в силе.
          </p>
          <Link
            to="/app/analysis"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-brand hover:underline"
          >
            Загрузить деталь вместе со STEP-моделью
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </Container>
    )
  }

  if (!approvalApproved || (!toolpathResult && !legacyPlan)) {
    return (
      <Container className="max-w-2xl py-10">
        <PageBackdrop />
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">Производство</h1>
        <p className="mb-8 text-sm text-ink-dim">
          Согласование комплекта технологической документации главным технологом.
        </p>

        <div className="rounded-2xl border border-border bg-surface p-6">
          {!approvalApproved && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              Комплект ещё не согласован — вернитесь на экран «Экспертиза НСИ» и согласуйте его там.
            </div>
          )}
          {approvalApproved && planMutation.isPending && (
            <p className="text-sm text-ink-dim">
              {pendingInput?.kind === 'metal'
                ? 'Расчёт управляющей программы по геометрии детали…'
                : 'Построение плана симуляции…'}
            </p>
          )}
          {approvalApproved && planMutation.isError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {(planMutation.error as Error).message}
            </div>
          )}
        </div>
      </Container>
    )
  }

  const partName = toolpathResult?.toolpath.part_name ?? legacyPlan?.part_name ?? '—'

  return (
    <Container className="max-w-3xl py-10">
      <PageBackdrop />
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">Комплект ТД согласован</h1>
      <p className="mb-8 text-sm text-ink-dim">Изготовление детали «{partName}»</p>

      <div className="rounded-2xl border border-border bg-surface p-6">
        {toolpathResult && pendingInput?.kind === 'metal' && pendingInput.stepModel && (
          <ToolpathSimulation response={toolpathResult} stepModel={pendingInput.stepModel} />
        )}
        {legacyPlan && <LegacySimulation plan={legacyPlan} />}
      </div>
    </Container>
  )
}
