import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { buildIiotGraph, CATEGORY_LABEL, type IiotNode } from '@/lib/iiotGraph'
import { STATUS_COLOR, STATUS_LABEL } from '@/lib/twinData'

const CATEGORY_COLOR: Record<string, string> = {
  control: 'var(--color-twin-purple)',
  infrastructure: 'var(--color-twin-blue)',
  process: 'var(--color-twin-cyan)',
  energy: 'var(--color-twin-yellow)',
}

const NODE_W = 148
const NODE_H = 56

function nodeCenter(node: IiotNode) {
  return { x: node.x + NODE_W / 2, y: node.y + NODE_H / 2 }
}

function EdgeLayer({
  nodes,
  edges,
  color,
  dashed,
  label,
}: {
  nodes: IiotNode[]
  edges: [string, string][]
  color: string
  dashed: boolean
  label: string
}) {
  return (
    <g>
      {edges.map(([fromId, toId]) => {
        const from = nodes.find((n) => n.id === fromId)
        const to = nodes.find((n) => n.id === toId)
        if (!from || !to) return null
        const a = nodeCenter(from)
        const b = nodeCenter(to)
        const mx = (a.x + b.x) / 2
        const my = (a.y + b.y) / 2 - 30
        return (
          <path
            key={`${label}-${fromId}-${toId}`}
            d={`M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`}
            fill="none"
            stroke={color}
            strokeWidth={dashed ? 1.4 : 2}
            strokeDasharray={dashed ? '3 6' : '8 6'}
            opacity={0.55}
          >
            <animate attributeName="stroke-dashoffset" values="0;-24" dur="1.4s" repeatCount="indefinite" />
          </path>
        )
      })}
    </g>
  )
}

function NodeCard({
  node,
  selected,
  onSelect,
}: {
  node: IiotNode
  selected: boolean
  onSelect: (id: string) => void
}) {
  const color = CATEGORY_COLOR[node.category]
  return (
    <g
      className="cursor-pointer"
      onClick={(e) => {
        e.stopPropagation()
        onSelect(node.id)
      }}
    >
      <rect
        x={node.x}
        y={node.y}
        width={NODE_W}
        height={NODE_H}
        rx={10}
        fill="#0d1929"
        stroke={selected ? color : '#263a51'}
        strokeWidth={selected ? 2 : 1}
        style={selected ? { filter: `drop-shadow(0 0 6px ${color})` } : undefined}
      />
      <circle cx={node.x + 14} cy={node.y + 14} r={4} fill={STATUS_COLOR[node.status]} />
      <text x={node.x + 26} y={node.y + 18} fontSize={10.5} fontWeight={650} fill="#e7f0fa">
        {node.name.length > 20 ? node.name.slice(0, 19) + '…' : node.name}
      </text>
      <text x={node.x + 14} y={node.y + 38} fontSize={8.5} fill="#8fa5bc">
        {CATEGORY_LABEL[node.category]}
      </text>
    </g>
  )
}

export function IiotGraph({ materialKind }: { materialKind: 'metal' | 'plastic' }) {
  const graph = useMemo(() => buildIiotGraph(materialKind), [materialKind])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showMaterial, setShowMaterial] = useState(true)
  const [showTelemetry, setShowTelemetry] = useState(true)
  const [showControl, setShowControl] = useState(true)

  const selectedNode = graph.nodes.find((n) => n.id === selectedId) ?? null

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-twin-border bg-twin-bg">
      <div className="absolute left-4 top-4 z-10 flex flex-col gap-2">
        <div className="rounded-xl border border-twin-border bg-[#0d1929]/90 p-3 backdrop-blur">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-twin-muted">
            Слои схемы
          </div>
          <div className="flex flex-col gap-1.5 text-[11px]">
            <LayerToggle label="Материальный поток" color="var(--color-twin-cyan)" value={showMaterial} onChange={setShowMaterial} />
            <LayerToggle label="IIoT-телеметрия" color="var(--color-twin-blue)" dashed value={showTelemetry} onChange={setShowTelemetry} />
            <LayerToggle label="Командная шина" color="var(--color-twin-purple)" dashed value={showControl} onChange={setShowControl} />
          </div>
        </div>
        <div className="rounded-xl border border-twin-border bg-[#0d1929]/90 p-3 backdrop-blur">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-twin-muted">
            Состояния
          </div>
          <div className="flex flex-col gap-1.5 text-[11px] text-twin-muted">
            {(['online', 'warning', 'alert'] as const).map((status) => (
              <div key={status} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_COLOR[status] }} />
                {STATUS_LABEL[status]}
              </div>
            ))}
          </div>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${graph.width} 480`}
        preserveAspectRatio="xMidYMid meet"
        className="h-full w-full"
        onClick={() => setSelectedId(null)}
      >
        <defs>
          <pattern id="iiotGrid" width={28} height={28} patternUnits="userSpaceOnUse">
            <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#152233" strokeWidth={1} />
          </pattern>
        </defs>
        <rect width={graph.width} height={480} fill="url(#iiotGrid)" />

        {showMaterial && (
          <EdgeLayer nodes={graph.nodes} edges={graph.materialEdges} color="var(--color-twin-cyan)" dashed={false} label="material" />
        )}
        {showTelemetry && (
          <EdgeLayer nodes={graph.nodes} edges={graph.telemetryEdges} color="var(--color-twin-blue)" dashed label="telemetry" />
        )}
        {showControl && (
          <EdgeLayer nodes={graph.nodes} edges={graph.controlEdges} color="var(--color-twin-purple)" dashed label="control" />
        )}

        {graph.nodes.map((node) => (
          <NodeCard key={node.id} node={node} selected={selectedId === node.id} onSelect={setSelectedId} />
        ))}
      </svg>

      <AnimatePresence>
        {selectedNode && (
          <motion.aside
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="absolute right-4 top-4 z-20 w-[280px] rounded-xl border border-[#284256] bg-[#0a1019]/97 backdrop-blur-xl"
          >
            <div className="flex items-start justify-between gap-3 border-b border-twin-border p-4">
              <div>
                <h4 className="text-sm font-semibold text-twin-text">{selectedNode.name}</h4>
                <div className="mt-1 text-[10px] text-twin-muted">{CATEGORY_LABEL[selectedNode.category]}</div>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="flex h-6 w-6 items-center justify-center rounded-md border border-twin-border bg-[#101a27] text-twin-muted hover:text-twin-text"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="p-4 text-xs">
              <p className="mb-3 leading-relaxed text-twin-muted">{selectedNode.description}</p>
              <div className="mb-3 flex items-center justify-between rounded-lg bg-[#101925] px-3 py-2">
                <span className="text-twin-muted">Статус</span>
                <span className="flex items-center gap-1.5" style={{ color: STATUS_COLOR[selectedNode.status] }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_COLOR[selectedNode.status] }} />
                  {STATUS_LABEL[selectedNode.status]}
                </span>
              </div>
              <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-[#61778c]">
                Промышленные протоколы
              </div>
              <div className="flex flex-wrap gap-1">
                {selectedNode.protocols.map((p) => (
                  <span
                    key={p}
                    className="rounded-md border border-twin-cyan/20 bg-twin-cyan/[0.06] px-1.5 py-0.5 text-[10px] text-twin-cyan/90"
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  )
}

function LayerToggle({
  label,
  color,
  dashed,
  value,
  onChange,
}: {
  label: string
  color: string
  dashed?: boolean
  value: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-twin-muted">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} className="accent-current" style={{ color }} />
      <svg width={18} height={2} className="shrink-0">
        <line x1={0} y1={1} x2={18} y2={1} stroke={color} strokeWidth={2} strokeDasharray={dashed ? '3 3' : undefined} />
      </svg>
      {label}
    </label>
  )
}
