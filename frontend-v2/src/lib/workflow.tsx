import { createContext, useContext, useState, type ReactNode } from 'react'

/**
 * Входные данные, полученные на экране "Анализ детали" и нужные
 * дальше в "Производстве"/"Контроле качества" — backend не хранит
 * состояние между запросами (каждый эндпоинт принимает файлы заново),
 * поэтому сами файлы и параметры печати переносятся между экранами
 * здесь, в памяти SPA, а не через backend.
 */
export type WorkflowInput =
  | { kind: 'metal'; drawing: File }
  | { kind: 'plastic'; stepModel: File; amTechnologyCode: string; materialGroupCode: string }

interface WorkflowState {
  pendingInput: WorkflowInput | null
  setPendingInput: (input: WorkflowInput | null) => void
  /**
   * Пройдена ли экспертиза НСИ для текущей детали (Модуль 1.2/1.3) —
   * блокирует прямой заход в "Производство" в обход этого шага
   * (главный технолог должен сначала увидеть сверку с НСИ, см. решение
   * пользователя от 2026-08-03). Сбрасывается при загрузке новой детали.
   */
  nsiExpertiseAcknowledged: boolean
  acknowledgeNsiExpertise: () => void
}

const WorkflowContext = createContext<WorkflowState | null>(null)

export function WorkflowProvider({ children }: { children: ReactNode }) {
  const [pendingInput, setPendingInputState] = useState<WorkflowInput | null>(null)
  const [nsiExpertiseAcknowledged, setNsiExpertiseAcknowledged] = useState(false)

  function setPendingInput(input: WorkflowInput | null) {
    setNsiExpertiseAcknowledged(false)
    setPendingInputState(input)
  }

  function acknowledgeNsiExpertise() {
    setNsiExpertiseAcknowledged(true)
  }

  return (
    <WorkflowContext.Provider
      value={{ pendingInput, setPendingInput, nsiExpertiseAcknowledged, acknowledgeNsiExpertise }}
    >
      {children}
    </WorkflowContext.Provider>
  )
}

export function useWorkflow(): WorkflowState {
  const ctx = useContext(WorkflowContext)
  if (!ctx) throw new Error('useWorkflow должен использоваться внутри WorkflowProvider')
  return ctx
}
