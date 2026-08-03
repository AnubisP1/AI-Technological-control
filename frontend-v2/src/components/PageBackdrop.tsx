import { GearBackdrop } from '@/components/GearBackdrop'

/**
 * Декоративный 3D-фон рабочих экранов приложения (Фаза 17, часть 2,
 * обновлено в части 5) — по прямому запросу пользователя показывает
 * узнаваемую шестерню (UI UX reference/gear.glb, готовая авторская
 * модель), а не абстрактную геометрию — приглушённая и закреплённая в
 * углу экрана, поскольку рабочие экраны — светлая тема с плотным UI
 * поверх (в отличие от тёмного полноэкранного Hero).
 *
 * compact — уменьшенный вариант для экранов с широким табличным
 * контентом до самого правого края (напр. реестр НСИ): полноразмерный
 * фон визуально задевал последнюю графу таблицы (найдено при проверке
 * через Playwright) — на таких экранах фон меньше и чуть прозрачнее.
 */
export function PageBackdrop({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={
        compact
          ? 'pointer-events-none fixed bottom-0 right-0 z-0 h-[30vh] w-[30vh] max-h-[300px] max-w-[300px] opacity-[0.1]'
          : 'pointer-events-none fixed bottom-0 right-0 z-0 h-[52vh] w-[52vh] max-h-[560px] max-w-[560px] opacity-[0.16]'
      }
      aria-hidden="true"
    >
      <GearBackdrop transparentBackground />
    </div>
  )
}
