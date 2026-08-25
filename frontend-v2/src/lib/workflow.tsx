import { createContext, useContext, useState, type ReactNode } from 'react'
import type {
  KdReviewReport,
  RouteCard,
  PrintRouteCardResponse,
  MaterialRecommendationOption,
} from '@/lib/api'

/**
 * Входные данные, полученные на экране "Анализ детали" и нужные
 * дальше в "Экспертизе НСИ"/"Производстве"/"Контроле качества" —
 * backend не хранит состояние между запросами (каждый эндпоинт
 * принимает файлы заново), поэтому сами файлы и параметры печати
 * переносятся между экранами здесь, в памяти SPA, а не через backend.
 *
 * review/routeCard (металл) и printCards (пластик) — уже ПОЛУЧЕННЫЙ на
 * AnalysisPage результат анализа, не только входные файлы (Фаза 20, по
 * прямому запросу пользователя: экран "Экспертиза НСИ" должен
 * открываться с готовыми данными, не запускать повторный вызов API и
 * не требовать отдельного нажатия "Запустить сверку" — анализ уже
 * выполнен один раз при загрузке детали).
 *
 * stepModel для металла (Фаза 22) — STEP обязателен для металлических
 * деталей: без него "Производство" не может построить реальный
 * фрезерный тулпас по геометрии (только легаси-симуляцию без геометрии,
 * см. ProductionPage.tsx), это осознанное ужесточение по сравнению с
 * прежним опциональным STEP на "Анализ детали".
 */
export type WorkflowInput =
  | { kind: 'metal'; drawing: File; stepModel: File; review: KdReviewReport; routeCard: RouteCard }
  | {
      kind: 'plastic'
      stepModel: File
      amTechnologyCode: string
      materialGroupCode: string
      printCards: PrintRouteCardResponse
      // Заполнение/число стенок/ориентация — из выбранной автоподбором
      // рекомендации, не из printCards (та не содержит этих полей) —
      // нужны для реестра экспертизы НСИ пластика.
      selectedOption: MaterialRecommendationOption
    }

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
  /**
   * Согласован ли комплект ТД главным технологом — решение теперь
   * принимается во всплывающем диалоге на экране "Экспертиза НСИ"
   * (см. ApprovalDialog.tsx), не на самой странице "Производство",
   * поэтому факт согласования нужно передать между экранами так же,
   * как pendingInput. Сбрасывается при загрузке новой детали.
   */
  approvalApproved: boolean
  markApproved: () => void
}

const WorkflowContext = createContext<WorkflowState | null>(null)

export function WorkflowProvider({ children }: { children: ReactNode }) {
  const [pendingInput, setPendingInputState] = useState<WorkflowInput | null>(null)
  const [nsiExpertiseAcknowledged, setNsiExpertiseAcknowledged] = useState(false)
  const [approvalApproved, setApprovalApproved] = useState(false)

  function setPendingInput(input: WorkflowInput | null) {
    setNsiExpertiseAcknowledged(false)
    setApprovalApproved(false)
    setPendingInputState(input)
  }

  function acknowledgeNsiExpertise() {
    setNsiExpertiseAcknowledged(true)
  }

  function markApproved() {
    setApprovalApproved(true)
  }

  return (
    <WorkflowContext.Provider
      value={{
        pendingInput,
        setPendingInput,
        nsiExpertiseAcknowledged,
        acknowledgeNsiExpertise,
        approvalApproved,
        markApproved,
      }}
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
