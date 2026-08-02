import { motion } from 'framer-motion'
import { Link } from 'react-router'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PartViewer } from '@/components/PartViewer'
import { StatusPill } from '@/components/layout/StatusPill'
import { Container } from '@/components/marketing/Section'

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-dark text-white">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            'linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      <Container className="relative grid gap-12 py-24 md:grid-cols-2 md:items-center md:py-32">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="flex flex-col gap-6"
        >
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-white/50">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-soft" />
            AI-Технолог · производство БПЛА
          </div>
          <h1 className="text-4xl font-bold leading-[1.08] tracking-tight text-balance md:text-6xl">
            От чертежа дрона до готовой техпроцесса —
            <span className="text-brand-soft"> за минуты, не дни</span>
          </h1>
          <p className="max-w-lg text-lg leading-relaxed text-white/60">
            Загрузите чертёж, спецификацию или STEP-модель детали БПЛА — система сверит её
            с базой нормативно-справочной информации, оценит технологичность и сама
            сформирует маршрутную и операционную карту. Работает полностью локально,
            без облака.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              size="lg"
              className="h-11 px-5 text-sm"
              nativeButton={false}
              render={<Link to="/app/analysis" />}
            >
              Открыть рабочее пространство
              <ArrowRight className="h-4 w-4" />
            </Button>
            <StatusPill />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.15 }}
          className="h-[340px] md:h-[440px]"
        >
          <PartViewer partName="Пропеллер БПЛА (пример)" lengthXMm={280} lengthYMm={280} lengthZMm={18} />
        </motion.div>
      </Container>
    </section>
  )
}
