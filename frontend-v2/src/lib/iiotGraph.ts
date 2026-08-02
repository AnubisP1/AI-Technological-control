import { TWIN_FACTORIES, type ZoneStatus } from '@/lib/twinData'

export type IiotNodeCategory = 'control' | 'infrastructure' | 'process' | 'energy'

export interface IiotNode {
  id: string
  name: string
  category: IiotNodeCategory
  x: number
  y: number
  status: ZoneStatus
  description: string
  protocols: string[]
}

const CATEGORY_LABEL: Record<IiotNodeCategory, string> = {
  control: 'Управление / MES',
  infrastructure: 'Инфраструктура',
  process: 'Производственный уровень',
  energy: 'Энергетика',
}

export { CATEGORY_LABEL }

// Общий IT/OT-контур — одинаковый для обеих схем (металл/пластик),
// перенос состава уровней из UI UX reference/visual factory.html.
const COMMON_NODES: IiotNode[] = [
  {
    id: 'cloud', name: 'MES / Облачная платформа', category: 'control',
    x: 640, y: 60, status: 'online',
    description: 'Централизованный сбор данных, диспетчеризация производства и аналитика цифрового двойника.',
    protocols: ['REST API', 'MQTT', 'OPC UA'],
  },
  {
    id: 'gateway', name: 'IIoT-шлюз', category: 'infrastructure',
    x: 640, y: 190, status: 'online',
    description: 'Edge-шлюз агрегирует телеметрию с производственных зон перед отправкой в MES.',
    protocols: ['OPC UA', 'MQTT', 'Modbus TCP'],
  },
  {
    id: 'network', name: 'Промышленная сеть', category: 'infrastructure',
    x: 380, y: 190, status: 'online',
    description: 'Резервированная сеть Ethernet/PROFINET, связывающая контроллеры оборудования.',
    protocols: ['PROFINET', 'EtherCAT', 'IO-Link'],
  },
  {
    id: 'safety', name: 'Система безопасности', category: 'infrastructure',
    x: 900, y: 190, status: 'online',
    description: 'Аварийные остановы, световые завесы, контроль доступа к опасным зонам.',
    protocols: ['Safety PLC', 'PROFIsafe'],
  },
  {
    id: 'energy', name: 'Энергоучёт', category: 'energy',
    x: 900, y: 60, status: 'online',
    description: 'Учёт потребления электроэнергии по цехам и отдельным группам оборудования.',
    protocols: ['Modbus TCP', 'OPC UA'],
  },
]

const PROCESS_NODE_GAP = 190
const PROCESS_NODE_START_X = 90

export function buildIiotGraph(materialKind: 'metal' | 'plastic') {
  const factory = TWIN_FACTORIES[materialKind]
  const processNodes: IiotNode[] = factory.zones.map((zone, index) => ({
    id: zone.id,
    name: zone.name,
    category: 'process',
    x: PROCESS_NODE_START_X + index * PROCESS_NODE_GAP,
    y: 380,
    status: zone.status,
    description: zone.description,
    protocols: zone.protocols,
  }))

  const materialEdges: [string, string][] = factory.flows
  const telemetryEdges: [string, string][] = processNodes.map((n) => [n.id, 'gateway'])
  const controlEdges: [string, string][] = [
    ['gateway', 'cloud'],
    ['network', 'gateway'],
    ['safety', 'network'],
    ['energy', 'cloud'],
  ]

  const width = PROCESS_NODE_START_X + (processNodes.length - 1) * PROCESS_NODE_GAP + 148 + 90
  // Общие узлы (MES/шлюз/сеть/безопасность/энергоучёт) центрируются над
  // производственной цепочкой независимо от её фактической ширины —
  // число зон отличается между металлом и пластиком.
  const centerX = width / 2
  const commonNodes: IiotNode[] = COMMON_NODES.map((node) => ({
    ...node,
    x: centerX + (node.x - 640),
  }))

  return {
    nodes: [...commonNodes, ...processNodes],
    materialEdges,
    telemetryEdges,
    controlEdges,
    width,
  }
}
