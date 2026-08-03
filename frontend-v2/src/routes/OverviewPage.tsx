import { Link } from 'react-router'
import { motion } from 'framer-motion'
import { ScanSearch, ClipboardCheck, Factory, ShieldCheck } from 'lucide-react'
import { Container } from '@/components/marketing/Section'
import { AssistantChatPanel } from '@/components/overview/AssistantChatPanel'

/**
 * "Обзор" (Фаза 17, часть 3, доработана в части 5) — сводная страница
 * рабочего пространства, по идее из UI UX reference/ai_technologist_site/
 * index.html. Вместо карточек "Состояние backend"/"Текущая деталь" (см.
 * git-историю) — по прямому запросу пользователя ("вместо состояния и
 * текущей детали добавь окно с чатом ИИ-Технологом") здесь окно чата с
 * AI-ассистентом по НСИ, см. AssistantChatPanel.
 */

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

export function OverviewPage() {
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

      <div className="mb-6 h-[420px]">
        <AssistantChatPanel />
      </div>

      <div className="mb-3 font-mono text-xs uppercase tracking-widest text-ink-dim">Сквозной путь системы</div>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-6 overflow-hidden rounded-2xl border border-border bg-surface"
      >
        <img
          src="/production-architecture.gif"
          alt="Схема цифрового контура технологической подготовки производства: от конструкторской документации до серийного производства"
          className="w-full"
        />
      </motion.div>
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
