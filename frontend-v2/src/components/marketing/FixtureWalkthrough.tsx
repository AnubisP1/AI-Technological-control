import { motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle, CircleHelp } from 'lucide-react'
import { Container, Section } from '@/components/marketing/Section'

/**
 * Реальный результат сквозного прогона на тестовом fixture (вал,
 * материал "45 ГОСТ 1050-2013", см. dev/PROGRESS.md, Фаза 3-4) —
 * значения зафиксированы по факту работы backend на реальной детали,
 * не выдуманы для витрины. Статичная витрина, не live-вызов API
 * (загрузка чертежа требует файла от пользователя).
 */
const REVIEW_ROWS = [
  { label: 'Материал', value: "45 ГОСТ 1050-2013 → Сталь 45", status: 'matched' as const },
  {
    label: 'Заготовка',
    value: 'Круг 67 ГОСТ 2590-2006 — типоразмер не в справочнике',
    status: 'partial' as const,
  },
  {
    label: 'Технические требования',
    value: '7 пунктов ТТ классифицировано по 5 категориям',
    status: 'matched' as const,
  },
]

const ROUTE_ROWS = [
  { op: '005', name: 'Токарная черновая', machine: '16К20' },
  { op: '010', name: 'Токарная чистовая', machine: '16К20' },
  { op: '015', name: 'Шлифовальная', machine: '3М151' },
]

const STATUS_STYLE = {
  matched: { icon: CheckCircle2, className: 'text-emerald-500' },
  partial: { icon: AlertTriangle, className: 'text-amber-500' },
  unknown: { icon: CircleHelp, className: 'text-ink-dim' },
} as const

export function FixtureWalkthrough() {
  return (
    <Section dark>
      <Container>
        <div className="mb-14 max-w-2xl">
          <div className="mb-3 font-mono text-xs uppercase tracking-widest text-brand-soft">
            Реальный прогон, не макет
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-balance md:text-4xl">
            Вот что система делает с реальным чертежом вала
          </h2>
          <p className="mt-4 text-white/60">
            Результат ниже — фактический вывод backend на тестовой детали проекта, не
            иллюстрация для презентации.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5 }}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-6"
          >
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-white/40">
              Модуль 1.2 · Оценка КД
            </div>
            <ul className="flex flex-col gap-3">
              {REVIEW_ROWS.map((row) => {
                const style = STATUS_STYLE[row.status]
                return (
                  <li key={row.label} className="flex items-start gap-3 text-sm">
                    <style.icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.className}`} />
                    <div>
                      <div className="text-white/40">{row.label}</div>
                      <div className="text-white/85">{row.value}</div>
                    </div>
                  </li>
                )
              })}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-6"
          >
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-white/40">
              Модуль 1.3 · Маршрутная карта
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40">
                  <th className="pb-2 font-normal">№</th>
                  <th className="pb-2 font-normal">Операция</th>
                  <th className="pb-2 font-normal">Оборудование</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {ROUTE_ROWS.map((row) => (
                  <tr key={row.op} className="border-t border-white/10">
                    <td className="py-2 text-white/50">{row.op}</td>
                    <td className="py-2 text-white/85">{row.name}</td>
                    <td className="py-2 text-brand-soft">{row.machine}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 text-xs text-white/40">
              Сверлильная операция не подобрана — станок в справочнике связан только с
              поковкой/отливкой, не с прокатом сортовым этой детали.
            </div>
          </motion.div>
        </div>
      </Container>
    </Section>
  )
}
