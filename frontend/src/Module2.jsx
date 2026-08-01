import { useEffect, useMemo, useRef, useState } from 'react'
import { decideApproval, simulateMetalManufacturing, simulatePrintManufacturing } from './api'
import MachineIcon from './MachineIcon'

const TOTAL_MS = 15000

function useSimulationClock(active, totalOperations) {
  const [elapsedMs, setElapsedMs] = useState(0)
  const rafRef = useRef(null)
  const startRef = useRef(null)

  useEffect(() => {
    if (!active || totalOperations === 0) return undefined

    startRef.current = performance.now()
    const tick = (now) => {
      const elapsed = Math.min(now - startRef.current, TOTAL_MS)
      setElapsedMs(elapsed)
      if (elapsed < TOTAL_MS) {
        rafRef.current = requestAnimationFrame(tick)
      }
    }
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [active, totalOperations])

  return elapsedMs
}

function operationBoundaries(operations) {
  const totalShare = operations.reduce((sum, op) => sum + op.duration_share, 0) || 1
  let acc = 0
  return operations.map((op) => {
    const startMs = (acc / totalShare) * TOTAL_MS
    acc += op.duration_share
    const endMs = (acc / totalShare) * TOTAL_MS
    return { ...op, startMs, endMs }
  })
}

function ProgramOutput({ lines, revealCount }) {
  if (lines.length === 0) {
    return <p className="muted">Для этой операции управляющая программа не формируется.</p>
  }
  return (
    <pre className="program-output">
      {lines.slice(0, revealCount).map((line, i) => (
        <div key={i}>{line}</div>
      ))}
      {revealCount < lines.length && <div className="cursor-blink">▍</div>}
    </pre>
  )
}

export default function Module2({ pendingInput, onQualityCheck }) {
  const [approval, setApproval] = useState(null)
  const [rejectComment, setRejectComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const [plan, setPlan] = useState(null)
  const [simulationStarted, setSimulationStarted] = useState(false)
  const [simulationDone, setSimulationDone] = useState(false)

  const operations = useMemo(
    () => (plan ? operationBoundaries(plan.operations) : []),
    [plan]
  )
  const elapsedMs = useSimulationClock(simulationStarted && !simulationDone, operations.length)

  useEffect(() => {
    if (simulationStarted && elapsedMs >= TOTAL_MS) {
      setSimulationDone(true)
    }
  }, [elapsedMs, simulationStarted])

  const progressPercent = Math.round((elapsedMs / TOTAL_MS) * 100)
  const currentOperationIndex = operations.findIndex(
    (op) => elapsedMs >= op.startMs && elapsedMs < op.endMs
  )
  const activeIndex = simulationDone
    ? operations.length - 1
    : currentOperationIndex === -1
      ? 0
      : currentOperationIndex

  async function handleApprove() {
    setBusy(true)
    setError(null)
    try {
      const result = await decideApproval({ decision: 'approved' })
      setApproval(result)

      if (!pendingInput) {
        setError('Нет входных данных из Модуля 1 — сначала сгенерируйте документацию.')
        return
      }
      const simulationResult =
        pendingInput.kind === 'metal'
          ? await simulateMetalManufacturing({ drawing: pendingInput.drawing })
          : await simulatePrintManufacturing({
              stepModel: pendingInput.stepModel,
              amTechnologyCode: pendingInput.amTechnologyCode,
              materialGroupCode: pendingInput.materialGroupCode,
            })
      setPlan(simulationResult.plan)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleReject() {
    if (!rejectComment.trim()) {
      setError('Укажите комментарий — что нужно исправить при повторной генерации.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await decideApproval({ decision: 'rejected', comment: rejectComment })
      setApproval(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function startSimulation() {
    setSimulationStarted(true)
    setSimulationDone(false)
  }

  if (!approval || !approval.can_start_simulation) {
    return (
      <div className="module2">
        <section className="card">
          <h2>Согласование комплекта ТД</h2>
          {!pendingInput && (
            <p className="muted">
              Сначала сгенерируйте маршрутную карту в разделе «Анализ КД».
            </p>
          )}
          <div className="field-row">
            <button type="button" disabled={busy} onClick={handleApprove}>
              Согласовать
            </button>
          </div>
          <div className="field-row">
            <input
              type="text"
              placeholder="Комментарий для повторной генерации"
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
            />
            <button type="button" className="btn-secondary" disabled={busy} onClick={handleReject}>
              Отклонить
            </button>
          </div>
          {error && <p className="error-text">{error}</p>}
          {approval?.decision === 'rejected' && (
            <p className="finding-warning">
              Комплект отклонён: «{approval.comment}». Вернитесь в Модуль 1 для повторной генерации.
            </p>
          )}
        </section>
      </div>
    )
  }

  return (
    <div className="module2">
      <section className="card">
        <h2>Комплект ТД согласован</h2>
        <p className="muted">Симуляция изготовления детали «{plan?.part_name || '—'}»</p>

        {!simulationStarted && (
          <button type="button" onClick={startSimulation} disabled={!plan || plan.operations.length === 0}>
            Запустить симуляцию изготовления
          </button>
        )}

        {plan && plan.operations.length === 0 && (
          <p className="error-text">
            Не удалось построить план симуляции — автоподбор техпроцесса не дал операций.
          </p>
        )}

        {simulationStarted && (
          <>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
            </div>
            <p className="muted">{progressPercent}% · {(elapsedMs / 1000).toFixed(1)} c из 15 c</p>

            {operations[activeIndex] && (
              <div className="simulation-active-op">
                <MachineIcon code={operations[activeIndex].machine_icon} />
                <div>
                  <div className="op-name">{operations[activeIndex].name}</div>
                  <div className="muted">{operations[activeIndex].machine_label}</div>
                </div>
              </div>
            )}

            <div className="operation-timeline">
              {operations.map((op, i) => (
                <div
                  key={op.sequence_no}
                  className={`timeline-step ${i === activeIndex ? 'timeline-step-active' : ''} ${
                    elapsedMs >= op.endMs ? 'timeline-step-done' : ''
                  }`}
                >
                  {i + 1}. {op.name}
                </div>
              ))}
            </div>

            {operations[activeIndex] && (
              <div className="program-panel">
                <h3>Управляющая программа — {operations[activeIndex].name}</h3>
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
              <button type="button" onClick={onQualityCheck}>
                Выполнить анализ качества изготовления
              </button>
            )}
          </>
        )}
      </section>
    </div>
  )
}
