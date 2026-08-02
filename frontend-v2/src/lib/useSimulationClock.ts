import { useEffect, useRef, useState } from 'react'

const TOTAL_MS = 15000

export function useSimulationClock(active: boolean, totalOperations: number): number {
  const [elapsedMs, setElapsedMs] = useState(0)
  const rafRef = useRef<number | null>(null)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    if (!active || totalOperations === 0) return undefined

    startRef.current = performance.now()
    const tick = (now: number) => {
      const elapsed = Math.min(now - (startRef.current ?? now), TOTAL_MS)
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

export { TOTAL_MS }

export interface OperationBoundary {
  startMs: number
  endMs: number
}

export function operationBoundaries<T extends { duration_share: number }>(
  operations: T[]
): (T & OperationBoundary)[] {
  const totalShare = operations.reduce((sum, op) => sum + op.duration_share, 0) || 1
  let acc = 0
  return operations.map((op) => {
    const startMs = (acc / totalShare) * TOTAL_MS
    acc += op.duration_share
    const endMs = (acc / totalShare) * TOTAL_MS
    return { ...op, startMs, endMs }
  })
}
