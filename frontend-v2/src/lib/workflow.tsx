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
}

const WorkflowContext = createContext<WorkflowState | null>(null)

export function WorkflowProvider({ children }: { children: ReactNode }) {
  const [pendingInput, setPendingInput] = useState<WorkflowInput | null>(null)
  return (
    <WorkflowContext.Provider value={{ pendingInput, setPendingInput }}>
      {children}
    </WorkflowContext.Provider>
  )
}

export function useWorkflow(): WorkflowState {
  const ctx = useContext(WorkflowContext)
  if (!ctx) throw new Error('useWorkflow должен использоваться внутри WorkflowProvider')
  return ctx
}
