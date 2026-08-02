import { useEffect, useState } from 'react'
import type { TwinZone } from '@/lib/twinData'

const TICK_MS = 3500

/**
 * Симуляция телеметрии цифрового двойника — целиком на фронте, без
 * запроса к backend (согласовано в плане Фазы 9: экран остаётся
 * иллюстративным по ТЗ, "здесь мы просто отображаем возможную
 * архитектуру"). Раз в TICK_MS слегка колеблет загрузку каждой зоны
 * (реалистичный шум, не случайный скачок) — создаёт впечатление живых
 * данных, не выдаёт себя за подключение к реальному оборудованию.
 */
export function useTwinSimulation(baseZones: TwinZone[]): TwinZone[] {
  const [zones, setZones] = useState(baseZones)

  useEffect(() => {
    setZones(baseZones)
  }, [baseZones])

  useEffect(() => {
    const interval = setInterval(() => {
      setZones((prev) =>
        prev.map((zone) => {
          if (zone.status === 'offline') return zone
          const jitter = Math.round((Math.random() - 0.5) * 6)
          const load = Math.min(99, Math.max(40, zone.load + jitter))
          return { ...zone, load }
        })
      )
    }, TICK_MS)
    return () => clearInterval(interval)
  }, [])

  return zones
}
