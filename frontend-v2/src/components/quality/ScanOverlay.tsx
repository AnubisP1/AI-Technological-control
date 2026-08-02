import { motion, AnimatePresence } from 'framer-motion'

/**
 * Визуальная симуляция процесса сравнения поверх реального результата
 * (реальное сравнение — OpenCV IoU по силуэту — занимает доли секунды,
 * см. dev/PROGRESS.md Фаза 6) — запрос к backend уходит сразу, эта
 * анимация только показывает пользователю сам факт сканирования, не
 * подменяет и не имитирует внутреннюю работу алгоритма.
 */
export function ScanOverlay({ active }: { active: boolean }) {
  return (
    <AnimatePresence>
      {active && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl"
        >
          <div className="absolute inset-0 bg-brand/10" />
          <motion.div
            className="absolute left-0 right-0 h-1 bg-brand-soft shadow-[0_0_16px_4px_rgba(125,168,255,0.7)]"
            initial={{ top: '0%' }}
            animate={{ top: ['0%', '100%', '0%'] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
          />
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                'repeating-linear-gradient(0deg, transparent, transparent 6px, rgba(255,255,255,0.5) 6px, rgba(255,255,255,0.5) 7px)',
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
