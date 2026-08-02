import { motion } from 'framer-motion'
import { FileSearch, PlayCircle, ScanEye, Cpu } from 'lucide-react'
import { Container, Section } from '@/components/marketing/Section'

const MODULES = [
  {
    icon: FileSearch,
    tag: 'Модуль 1',
    title: 'Анализ и генерация',
    body: 'Распознаёт чертёж, спецификацию и STEP-модель, сверяет их с базой НСИ, оценивает технологичность конструкции и формирует маршрутную и операционную карту.',
  },
  {
    icon: PlayCircle,
    tag: 'Модуль 2',
    title: 'Контроль и исполнение',
    body: 'Главный технолог согласует сформированную документацию — интерфейс показывает пошаговую симуляцию изготовления с построчной генерацией управляющей программы.',
  },
  {
    icon: ScanEye,
    tag: 'Модуль 3',
    title: 'Оценка качества',
    body: 'По фотографии готовой детали система сверяет её с 3D-моделью, определяет вероятные дефекты и либо формирует план устранения брака, либо готовит документы для серийного запуска.',
  },
  {
    icon: Cpu,
    tag: 'Модуль 4',
    title: 'Серийное производство',
    body: 'Показывает архитектуру цифрового двойника цеха — исполнительные механизмы, датчики контроля и каналы передачи телеметрии для металлического и полимерного участков.',
  },
] as const

export function HowItWorks() {
  return (
    <Section>
      <Container>
        <div className="mb-14 max-w-2xl">
          <div className="mb-3 font-mono text-xs uppercase tracking-widest text-brand">
            Как это работает
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-balance md:text-4xl">
            Четыре модуля — один сквозной путь от КД до серии
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {MODULES.map((module, index) => (
            <motion.div
              key={module.tag}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, delay: index * 0.08, ease: 'easeOut' }}
              className="group rounded-2xl border border-border bg-surface p-7 transition-shadow hover:shadow-lg hover:shadow-brand/5"
            >
              <div className="mb-5 flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand">
                  <module.icon className="h-5 w-5" />
                </span>
                <span className="font-mono text-xs uppercase tracking-widest text-ink-dim">
                  {module.tag}
                </span>
              </div>
              <h3 className="mb-2 text-xl font-semibold tracking-tight">{module.title}</h3>
              <p className="text-sm leading-relaxed text-ink-dim">{module.body}</p>
            </motion.div>
          ))}
        </div>
      </Container>
    </Section>
  )
}
