import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import {
  TWIN_FACTORIES,
  STATUS_COLOR,
  STATUS_LABEL,
  type TwinZone,
  type ZoneStatus,
} from '@/lib/twinData'
import { isoPoint, pointsString, floorPolygon, boxPolygons, zoneCenter } from '@/lib/isometry'
import { useTwinSimulation } from '@/lib/useTwinSimulation'

function ZoneMachineDetails({ zone }: { zone: TwinZone }) {
  const rows = zone.d >= 3 ? 2 : 1
  const columns = zone.w >= 4 ? 4 : 3
  const boxes: React.ReactNode[] = []

  for (let row = 0; row < rows; row++) {
    for (let column = 0; column < columns; column++) {
      const localX = zone.x + 0.6 + column * ((zone.w - 1.2) / columns)
      const localY = zone.y + 0.6 + row * ((zone.d - 1.1) / rows)
      const small = boxPolygons(localX, localY, 0.42, 0.42, zone.height + 14 + (column % 2) * 4)
      boxes.push(
        <g key={`${row}-${column}`}>
          <polygon points={pointsString(small.left)} fill="#17212d" stroke="#435266" strokeWidth={0.5} />
          <polygon points={pointsString(small.right)} fill="#101822" stroke="#435266" strokeWidth={0.5} />
          <polygon points={pointsString(small.top)} fill="#718094" stroke="#9aa8b6" strokeWidth={0.5} />
        </g>
      )
    }
  }

  const accentStart = isoPoint(zone.x + 0.35, zone.y + zone.d - 0.25, zone.height + 1)
  const accentEnd = isoPoint(zone.x + zone.w - 0.35, zone.y + zone.d - 0.25, zone.height + 1)

  return (
    <>
      {boxes}
      <line
        x1={accentStart.x}
        y1={accentStart.y}
        x2={accentEnd.x}
        y2={accentEnd.y}
        stroke="var(--color-twin-cyan)"
        strokeWidth={2.5}
        opacity={0.75}
      />
    </>
  )
}

function ZoneGroup({
  zone,
  selected,
  showLabels,
  showTelemetry,
  onSelect,
}: {
  zone: TwinZone
  selected: boolean
  showLabels: boolean
  showTelemetry: boolean
  onSelect: (id: string) => void
}) {
  const floor = floorPolygon(zone.x, zone.y, zone.w, zone.d)
  const box = boxPolygons(zone.x + 0.25, zone.y + 0.25, zone.w - 0.5, zone.d - 0.5, zone.height)
  const center = zoneCenter(zone, zone.height + 7)
  const statusColor = STATUS_COLOR[zone.status]

  return (
    <g
      onClick={(e) => {
        e.stopPropagation()
        onSelect(zone.id)
      }}
      className="cursor-pointer"
    >
      {zone.status === 'alert' && (
        <ellipse
          cx={center.x}
          cy={center.y + 16}
          rx={65}
          ry={27}
          fill="rgba(255,83,100,.1)"
          stroke="var(--color-twin-red)"
          strokeWidth={2}
        >
          <animate attributeName="opacity" values="1;0.25;1" dur="1.2s" repeatCount="indefinite" />
        </ellipse>
      )}

      <polygon
        points={pointsString(floor)}
        fill={zone.status === 'alert' ? 'rgba(255,83,100,.18)' : 'rgba(37,226,209,.035)'}
        stroke={zone.status === 'alert' ? 'var(--color-twin-red)' : '#31485a'}
        strokeWidth={1.2}
        className={selected ? 'drop-shadow-[0_0_6px_var(--color-twin-cyan)]' : ''}
      />

      <polygon points={pointsString(box.left)} fill="#253140" stroke="#526174" strokeWidth={0.8} />
      <polygon points={pointsString(box.right)} fill="#18222f" stroke="#46566a" strokeWidth={0.8} />
      <polygon points={pointsString(box.top)} fill={zone.color} stroke="#78899c" strokeWidth={0.8} />

      <ZoneMachineDetails zone={zone} />

      <circle
        cx={center.x}
        cy={center.y - 13}
        r={5}
        fill={statusColor}
        style={
          zone.status === 'alert'
            ? { animation: 'twinBlink 0.8s infinite' }
            : undefined
        }
      />

      {showTelemetry && (
        <>
          <circle cx={center.x} cy={center.y - 13} r={10} fill="none" stroke="var(--color-twin-cyan)" strokeWidth={1.2} opacity={0.4}>
            <animate attributeName="r" values="8;20" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.6;0" dur="2s" repeatCount="indefinite" />
          </circle>
        </>
      )}

      {showLabels && (
        <g pointerEvents="none">
          <rect
            x={center.x - 63}
            y={center.y + 25}
            width={126}
            height={31}
            rx={6}
            fill="rgba(6,11,18,.88)"
            stroke="rgba(68,93,115,.8)"
          />
          <text x={center.x} y={center.y + 39} textAnchor="middle" fontSize={10} fontWeight={700} fill="#b8c8d7">
            {zone.name}
          </text>
          <text x={center.x} y={center.y + 50} textAnchor="middle" fontSize={7} fill="#60768b">
            Загрузка {zone.load}% · {STATUS_LABEL[zone.status]}
          </text>
        </g>
      )}
    </g>
  )
}

function MaterialFlows({ zones, flows }: { zones: TwinZone[]; flows: [string, string][] }) {
  return (
    <>
      {flows.map(([fromId, toId]) => {
        const from = zones.find((z) => z.id === fromId)
        const to = zones.find((z) => z.id === toId)
        if (!from || !to) return null
        const a = zoneCenter(from, 15)
        const b = zoneCenter(to, 15)
        const mx = (a.x + b.x) / 2
        const my = Math.min(a.y, b.y) - 14
        return (
          <path
            key={`${fromId}-${toId}`}
            d={`M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`}
            fill="none"
            stroke="var(--color-twin-cyan)"
            strokeWidth={3}
            strokeDasharray="9 7"
            opacity={0.7}
            markerEnd="url(#twinFlowArrow)"
          >
            <animate attributeName="stroke-dashoffset" values="0;-32" dur="1.2s" repeatCount="indefinite" />
          </path>
        )
      })}
    </>
  )
}

function TelemetryFlows({ zones }: { zones: TwinZone[] }) {
  const gateway = isoPoint(17.2, 0.6, 85)
  return (
    <>
      <circle cx={gateway.x} cy={gateway.y} r={13} fill="#101c28" stroke="var(--color-twin-blue)" strokeWidth={2} />
      <text x={gateway.x} y={gateway.y + 3} textAnchor="middle" fontSize={9} fill="#76b8ff">
        IIoT
      </text>
      {zones.map((zone) => {
        const start = zoneCenter(zone, zone.height + 10)
        return (
          <path
            key={zone.id}
            d={`M ${start.x} ${start.y} Q ${(start.x + gateway.x) / 2} ${Math.min(start.y, gateway.y) - 35} ${gateway.x} ${gateway.y}`}
            fill="none"
            stroke="var(--color-twin-blue)"
            strokeWidth={1.5}
            strokeDasharray="3 7"
            opacity={0.6}
          >
            <animate attributeName="stroke-dashoffset" values="0;30" dur="1.5s" repeatCount="indefinite" />
          </path>
        )
      })}
    </>
  )
}

function FloorGrid() {
  const lines: React.ReactNode[] = []
  for (let x = 0; x <= 18; x++) {
    const start = isoPoint(x, 0, 11)
    const end = isoPoint(x, 11, 11)
    lines.push(<line key={`x${x}`} x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke="#1a2734" strokeWidth={1} opacity={0.7} />)
  }
  for (let y = 0; y <= 11; y++) {
    const start = isoPoint(0, y, 11)
    const end = isoPoint(18, y, 11)
    lines.push(<line key={`y${y}`} x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke="#1a2734" strokeWidth={1} opacity={0.7} />)
  }
  return <>{lines}</>
}

export function IsometricFactory({ materialKind }: { materialKind: 'metal' | 'plastic' }) {
  const baseFactory = TWIN_FACTORIES[materialKind]
  const zones = useTwinSimulation(baseFactory.zones)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showMaterial, setShowMaterial] = useState(true)
  const [showTelemetry, setShowTelemetry] = useState(true)
  const [showLabels, setShowLabels] = useState(true)

  const selectedZone = useMemo(() => zones.find((z) => z.id === selectedId) ?? null, [zones, selectedId])
  const factoryFloor = useMemo(() => boxPolygons(0, 0, 18, 11, 10), [])

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-twin-border bg-twin-bg">
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(circle at 50% 20%, rgba(37,226,209,0.04), transparent 40%)' }}
      />

      <div className="absolute left-1/2 top-3 z-10 flex -translate-x-1/2 items-center gap-1 rounded-xl border border-twin-border bg-[#090f18]/90 p-1 backdrop-blur">
        {[
          ['material', 'Материальный поток', showMaterial, setShowMaterial],
          ['telemetry', 'Телеметрия', showTelemetry, setShowTelemetry],
          ['labels', 'Подписи', showLabels, setShowLabels],
        ].map(([key, title, value, setter]) => (
          <button
            key={key as string}
            title={title as string}
            onClick={() => (setter as (v: boolean) => void)(!(value as boolean))}
            className={
              'rounded-lg px-2.5 py-1.5 text-[11px] transition-colors ' +
              (value ? 'bg-twin-cyan/15 text-twin-cyan' : 'text-twin-muted hover:text-twin-text')
            }
          >
            {title as string}
          </button>
        ))}
      </div>

      <div className="absolute left-4 top-16 z-10">
        <h3 className="text-base font-semibold tracking-tight text-twin-text">{baseFactory.title}</h3>
        <p className="mt-1 text-xs text-twin-muted">Интерактивный цифровой двойник · симулированные данные</p>
      </div>

      <svg
        viewBox="0 0 1200 780"
        className="h-full w-full"
        onClick={() => setSelectedId(null)}
      >
        <defs>
          <marker id="twinFlowArrow" markerWidth={7} markerHeight={7} refX={6} refY={3.5} orient="auto" viewBox="0 0 7 7">
            <path d="M0,0 L7,3.5 L0,7 z" fill="var(--color-twin-cyan)" />
          </marker>
        </defs>

        <ellipse cx={590} cy={565} rx={505} ry={150} fill="#030609" opacity={0.45} />

        <polygon points={pointsString(factoryFloor.left)} fill="#090e16" stroke="#243343" />
        <polygon points={pointsString(factoryFloor.right)} fill="#0b111b" stroke="#243343" />
        <polygon points={pointsString(factoryFloor.top)} fill="#151e2a" stroke="#314154" strokeWidth={2} />

        <FloorGrid />
        {showTelemetry && <TelemetryFlows zones={zones} />}
        {showMaterial && <MaterialFlows zones={zones} flows={baseFactory.flows} />}

        {zones.map((zone) => (
          <ZoneGroup
            key={zone.id}
            zone={zone}
            selected={selectedId === zone.id}
            showLabels={showLabels}
            showTelemetry={showTelemetry}
            onSelect={setSelectedId}
          />
        ))}
      </svg>

      <AnimatePresence>
        {selectedZone && (
          <motion.aside
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="absolute right-4 top-16 z-20 max-h-[calc(100%-90px)] w-[280px] overflow-y-auto rounded-xl border border-[#284256] bg-[#0a1019]/97 backdrop-blur-xl"
          >
            <div className="flex items-start justify-between gap-3 border-b border-twin-border p-4">
              <div>
                <h4 className="text-sm font-semibold text-twin-text">{selectedZone.name}</h4>
                <div className="mt-1 text-[10px] text-twin-muted">{selectedZone.type}</div>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="flex h-6 w-6 items-center justify-center rounded-md border border-twin-border bg-[#101a27] text-twin-muted hover:text-twin-text"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="p-4 text-xs">
              <p className="mb-3 leading-relaxed text-twin-muted">{selectedZone.description}</p>

              <div className="mb-3 flex items-center justify-between rounded-lg bg-[#101925] px-3 py-2">
                <span className="text-twin-muted">Состояние оборудования</span>
                <span className="flex items-center gap-1.5" style={{ color: STATUS_COLOR[selectedZone.status] }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_COLOR[selectedZone.status] }} />
                  {STATUS_LABEL[selectedZone.status]}
                </span>
              </div>

              <DetailSection title="Производственные показатели">
                <DetailMetric label="Текущая загрузка" value={`${selectedZone.load}%`} />
                <DetailMetric label="Время цикла" value={selectedZone.cycle} />
                <DetailMetric label="Выпуск за смену" value={`${selectedZone.output} шт.`} />
                <DetailMetric
                  label="Доступность"
                  value={selectedZone.status === 'alert' ? '63.4%' : '98.7%'}
                />
              </DetailSection>

              <DetailSection title="Датчики и контроль">
                <TagList items={selectedZone.sensors} />
              </DetailSection>

              <DetailSection title="Промышленные протоколы">
                <TagList items={selectedZone.protocols} />
              </DetailSection>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <style>{`
        @keyframes twinBlink { 50% { opacity: 0.25; } }
      `}</style>
    </div>
  )
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-3">
      <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-[#61778c]">{title}</div>
      {children}
    </div>
  )
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-white/5 py-1.5 text-[11px] text-[#8799aa]">
      <span>{label}</span>
      <strong className="text-[#d8e3ed]">{value}</strong>
    </div>
  )
}

function TagList({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-md border border-twin-cyan/20 bg-twin-cyan/[0.06] px-1.5 py-0.5 text-[10px] text-twin-cyan/90"
        >
          {item}
        </span>
      ))}
    </div>
  )
}

export type { ZoneStatus }
