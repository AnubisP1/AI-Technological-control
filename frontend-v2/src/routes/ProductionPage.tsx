import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router'
import { motion } from 'framer-motion'
import { PlayCircle, ArrowRight, ClipboardCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/marketing/Section'
import { MachineIcon } from '@/components/production/MachineIcon'
import { PageBackdrop } from '@/components/PageBackdrop'
import { useSimulationClock, operationBoundaries, TOTAL_MS } from '@/lib/useSimulationClock'
import { useWorkflow } from '@/lib/workflow'
import { simulateMetalManufacturing, simulatePrintManufacturing, type SimulationPlan } from '@/lib/api'

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

export function ProductionPage() {
  const navigate = useNavigate()
  const { pendingInput, nsiExpertiseAcknowledged, approvalApproved } = useWorkflow()
  const readyForApproval = Boolean(pendingInput) && nsiExpertiseAcknowledged

  const [plan, setPlan] = useState<SimulationPlan | null>(null)
  const [simulationStarted, setSimulationStarted] = useState(false)
  const [simulationDone, setSimulationDone] = useState(false)

  const operations = useMemo(() => (plan ? operationBoundaries(plan.operations) : []), [plan])
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

  // Решение о согласовании принимается в ApprovalDialog на экране
  // "Экспертиза НСИ" (Фаза 17, часть 5) — сюда попадают уже с
  // approvalApproved=true, поэтому план симуляции строится сразу,
  // без повторного запроса решения на этой странице.
  const planMutation = useMutation({
    mutationFn: async () => {
      if (!pendingInput) throw new Error('Нет входных данных — сначала пройдите «Анализ детали».')
      const simulationResult =
        pendingInput.kind === 'metal'
          ? await simulateMetalManufacturing({ drawing: pendingInput.drawing })
          : await simulatePrintManufacturing({
              stepModel: pendingInput.stepModel,
              amTechnologyCode: pendingInput.amTechnologyCode,
              materialGroupCode: pendingInput.materialGroupCode,
            })
      setPlan(simulationResult.plan)
    },
  })

  useEffect(() => {
    if (readyForApproval && approvalApproved && !plan && !planMutation.isPending) {
      planMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyForApproval, approvalApproved])

  function startSimulation() {
    setSimulationStarted(true)
    setSimulationDone(false)
  }

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

  if (!approvalApproved || !plan) {
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
            <p className="text-sm text-ink-dim">Построение плана симуляции…</p>
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

  return (
    <Container className="max-w-3xl py-10">
      <PageBackdrop />
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">
        Комплект ТД согласован
      </h1>
      <p className="mb-8 text-sm text-ink-dim">
        Симуляция изготовления детали «{plan?.part_name || '—'}»
      </p>

      <div className="rounded-2xl border border-border bg-surface p-6">
        {!simulationStarted && (
          <Button disabled={!plan || plan.operations.length === 0} onClick={startSimulation}>
            <PlayCircle className="h-4 w-4" />
            Запустить симуляцию изготовления
          </Button>
        )}

        {plan && plan.operations.length === 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            Не удалось построить план симуляции — автоподбор техпроцесса не дал операций.
          </div>
        )}

        {simulationStarted && (
          <div className="flex flex-col gap-5">
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
          </div>
        )}
      </div>
    </Container>
  )
}
