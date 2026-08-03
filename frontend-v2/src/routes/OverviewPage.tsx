import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { motion } from 'framer-motion'
import { ScanSearch, ClipboardCheck, Factory, ShieldCheck, FileText, ArrowRight } from 'lucide-react'
import { Container } from '@/components/marketing/Section'
import { useWorkflow } from '@/lib/workflow'

/**
 * "Обзор" (Фаза 17, часть 3) — сводная страница рабочего пространства,
 * по идее из UI UX reference/ai_technologist_site/index.html. В отличие
 * от прототипа (выдуманные метрики "96.8% уверенность AI", "Al 7075-T6",
 * "12 документов" для несуществующего проекта AI-TX-0248), здесь
 * показаны только реальные факты: статус backend через /health (тот же
 * запрос, что уже использует StatusPill) и состояние текущей загруженной
 * детали из WorkflowProvider — до загрузки детали карточка честно
 * говорит "деталь не загружена", а не показывает похожий на реальный,
 * но фиктивный проект.
 */

interface HealthResponse {
  status: string
  cpu_thread_budget: number
  cpu_count_total: number
}

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error('Backend недоступен')
  return response.json()
}

const MODULES = [
  {
    to: '/app/analysis',
    icon: ScanSearch,
    num: '01 / ANALYZE',
    title: 'Анализ детали',
    body: 'Распознавание чертежа, спецификации и STEP-модели, сверка с НСИ, генерация маршрутной и операционной карты.',
  },
  {
    to: '/app/nsi-expertise',
    icon: ClipboardCheck,
    num: '02 / VERIFY',
    title: 'Экспертиза НСИ',
    body: 'Реестр соответствия материала, заготовки и технических требований справочнику НСИ с фильтрами.',
  },
  {
    to: '/app/production',
    icon: Factory,
    num: '03 / EXECUTE',
    title: 'Производство',
    body: 'Согласование техдокументации и симуляция изготовления с построчной генерацией управляющей программы.',
  },
  {
    to: '/app/quality',
    icon: ShieldCheck,
    num: '04 / INSPECT',
    title: 'Контроль качества',
    body: 'Сравнение фото изготовленной детали с эталоном, план серийного запуска или рекомендации по браку.',
  },
] as const

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`rounded-2xl border border-border bg-surface p-6 ${className}`}
    >
      {children}
    </motion.div>
  )
}

export function OverviewPage() {
  const { pendingInput } = useWorkflow()
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, refetchInterval: 15_000 })

  const partLabel =
    pendingInput?.kind === 'metal'
      ? pendingInput.drawing.name
      : pendingInput?.kind === 'plastic'
        ? pendingInput.stepModel.name
        : null

  return (
    <Container className="max-w-6xl py-10">
      <div className="mb-8">
        <div className="mb-2 font-mono text-xs uppercase tracking-widest text-brand">AI manufacturing workspace</div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Обзор</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-dim">
          Единая точка входа в четыре модуля системы — от анализа конструкторской документации до контроля
          качества готового изделия.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <div className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-dim">Состояние backend</div>
          {health.isLoading && <div className="text-sm text-ink-dim">Проверка соединения…</div>}
          {health.isError && <div className="text-sm text-red-600">Backend недоступен</div>}
          {health.data && (
            <div className="flex items-center gap-6">
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-ink">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  Локальный контур активен
                </div>
                <div className="mt-1 text-xs text-ink-dim">Офлайн — без обращений к внешним сервисам</div>
              </div>
              <div className="ml-auto text-right">
                <div className="text-2xl font-bold tabular-nums text-ink">
                  {health.data.cpu_thread_budget}/{health.data.cpu_count_total}
                </div>
                <div className="text-[11px] text-ink-dim">потоков CPU-бюджета</div>
              </div>
            </div>
          )}
        </Card>

        <Card>
          <div className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-dim">Текущая деталь</div>
          {partLabel ? (
            <div>
              <div className="text-sm font-medium text-ink">{partLabel}</div>
              <div className="mt-1 text-xs text-ink-dim">
                {pendingInput?.kind === 'metal' ? 'Металл — маршрут механообработки' : 'Пластик — аддитивное производство'}
              </div>
              <Link
                to="/app/documents"
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:underline"
              >
                <FileText className="h-3.5 w-3.5" />
                Перейти к документам
              </Link>
            </div>
          ) : (
            <div>
              <div className="text-sm text-ink-dim">Деталь ещё не загружена.</div>
              <Link
                to="/app/analysis"
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:underline"
              >
                Загрузить чертёж или STEP-модель
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          )}
        </Card>
      </div>

      <div className="mb-3 font-mono text-xs uppercase tracking-widest text-ink-dim">Сквозной путь системы</div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {MODULES.map((m, i) => (
          <Link key={m.to} to={m.to}>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="group h-full rounded-2xl border border-border bg-surface p-5 transition-shadow hover:shadow-lg hover:shadow-brand/5"
            >
              <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-xl bg-brand/10 text-brand">
                <m.icon className="h-4 w-4" />
              </div>
              <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-ink-dim">{m.num}</div>
              <h3 className="mb-2 text-sm font-semibold text-ink">{m.title}</h3>
              <p className="text-xs leading-relaxed text-ink-dim">{m.body}</p>
            </motion.div>
          </Link>
        ))}
      </div>
    </Container>
  )
}
