import { useState } from 'react'
import { Boxes, Network } from 'lucide-react'
import { cn } from '@/lib/utils'
import { IsometricFactory } from '@/components/twin/IsometricFactory'
import { IiotGraph } from '@/components/twin/IiotGraph'

type MaterialKind = 'metal' | 'plastic'
type ViewMode = 'floor' | 'graph'

export function DigitalTwinPage() {
  const [materialKind, setMaterialKind] = useState<MaterialKind>('metal')
  const [viewMode, setViewMode] = useState<ViewMode>('floor')

  return (
    <div className="flex h-[calc(100vh-56px)] flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Цифровой двойник</h1>
          <p className="mt-1 text-sm text-ink-dim">
            Иллюстративная архитектура цеха и IIoT-контура — симулированная телеметрия,
            не подключение к реальному оборудованию.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg bg-muted p-1 text-sm">
            {(
              [
                ['metal', 'Металл'],
                ['plastic', 'Пластик'],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                onClick={() => setMaterialKind(value)}
                className={cn(
                  'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                  materialKind === value ? 'bg-surface text-ink shadow-sm' : 'text-ink-dim'
                )}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 rounded-lg bg-muted p-1 text-sm">
            <button
              onClick={() => setViewMode('floor')}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                viewMode === 'floor' ? 'bg-surface text-ink shadow-sm' : 'text-ink-dim'
              )}
            >
              <Boxes className="h-3.5 w-3.5" />
              Схема цеха
            </button>
            <button
              onClick={() => setViewMode('graph')}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                viewMode === 'graph' ? 'bg-surface text-ink shadow-sm' : 'text-ink-dim'
              )}
            >
              <Network className="h-3.5 w-3.5" />
              IIoT-архитектура
            </button>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        {viewMode === 'floor' ? (
          <IsometricFactory materialKind={materialKind} />
        ) : (
          <IiotGraph materialKind={materialKind} />
        )}
      </div>
    </div>
  )
}
