import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, PlayCircle, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/marketing/Section'
import { MachineIcon } from '@/components/production/MachineIcon'
import { PageBackdrop } from '@/components/PageBackdrop'
import { useSimulationClock, operationBoundaries, TOTAL_MS } from '@/lib/useSimulationClock'
import { useWorkflow } from '@/lib/workflow'
import {
  decideApproval,
  simulateMetalManufacturing,
  simulatePrintManufacturing,
  type ApprovalResult,
  type SimulationPlan,
} from '@/lib/api'

// Реальные габариты пропеллера БПЛА из тестового fixture (КД для
// тестов/Пластиковые детали/Архив/HQProp T5x3.STEP), полученные через
// RegexStepParser — тонкая деталь хорошо иллюстрирует тему
// производства/изготовления на этом экране.
const BACKGROUND_PART = { partName: 'HQProp T5x3', lengthXMm: 127.0, lengthYMm: 3.0, lengthZMm: 14.0 }

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
  const { pendingInput } = useWorkflow()

  const [approval, setApproval] = useState<ApprovalResult | null>(null)
  const [rejectComment, setRejectComment] = useState('')
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

  const approveMutation = useMutation({
    mutationFn: async () => {
      const result = await decideApproval({ decision: 'approved' })
      setApproval(result)
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

  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!rejectComment.trim()) throw new Error('Укажите комментарий — что нужно исправить.')
      const result = await decideApproval({ decision: 'rejected', comment: rejectComment })
      setApproval(result)
    },
  })

  function startSimulation() {
    setSimulationStarted(true)
    setSimulationDone(false)
  }

  if (!approval?.can_start_simulation) {
    return (
      <Container className="max-w-2xl py-10">
        <PageBackdrop {...BACKGROUND_PART} />
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-ink">Производство</h1>
        <p className="mb-8 text-sm text-ink-dim">
          Согласование комплекта технологической документации главным технологом.
        </p>

        <div className="rounded-2xl border border-border bg-surface p-6">
          {!pendingInput && (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              Сначала сгенерируйте документацию на экране «Анализ детали».
            </div>
          )}
          <div className="flex gap-3">
            <Button disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
              <CheckCircle2 className="h-4 w-4" />
              Согласовать
            </Button>
          </div>
          <div className="mt-4 flex gap-2">
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
          {approval?.decision === 'rejected' && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              Комплект отклонён: «{approval.comment}». Вернитесь в «Анализ детали» для повторной генерации.
            </div>
          )}
        </div>
      </Container>
    )
  }

  return (
    <Container className="max-w-3xl py-10">
      <PageBackdrop {...BACKGROUND_PART} />
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
