import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Environment, Center, Bounds } from '@react-three/drei'
import { InstancedMesh, Object3D, Color, BufferGeometry, Mesh } from 'three'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { cn } from '@/lib/utils'
import { fetchStepMesh } from '@/lib/api'
import type { MaterialRemovalSimulation, VoxelGridSpec, ToolpathOperation } from '@/lib/api'

/**
 * Честная voxel-симуляция реального съёма материала (Фаза 22, по
 * прямому запросу пользователя, доработано по прямой обратной связи
 * после первой версии: "должно отображать как фреза убирает постепенно
 * материал и из заготовки в процессе изготовления появляется модель
 * детали... размеры заготовки полупрозрачным голубым, модель которая
 * должна получиться — зелёным, фреза — красным").
 *
 * Три слоя геометрии в одном мировом пространстве координат (мм, то же,
 * что использует backend для stock_bounding_box_mm/moves):
 * - StockVoxels — голубые полупрозрачные воксели заготовки, тают по
 *   мере съёма (та же логика removal-событий, что была в первой версии).
 * - TargetModel — зелёная целевая модель, реальная тесселяция STEP
 *   через уже существующий пайплайн (fetchStepMesh/step_mesh_exporter.py,
 *   тот же, что PartViewer.tsx использует для точной геометрии) — не
 *   выдуманный контур, а честная реальная геометрия детали.
 * - ToolCursor — красный цилиндр-фреза, положение интерполируется вдоль
 *   moves активной операции синхронно с прогрессом voxel-анимации.
 */

const _ANIMATION_DURATION_MS = 22000
const _DUMMY = new Object3D()
const _STOCK_COLOR = new Color('#38BDF8')
const _TARGET_COLOR = new Color('#22C55E')
const _TOOL_COLOR = new Color('#EF4444')

interface ToolpathViewerProps {
  simulation: MaterialRemovalSimulation
  operations: ToolpathOperation[]
  stepModel: File
  playing: boolean
  onProgress?: (currentStep: number, totalSteps: number) => void
}

function voxelWorldPosition(grid: VoxelGridSpec, x: number, y: number, z: number): [number, number, number] {
  const [ox, oy, oz] = grid.origin_mm
  const s = grid.voxel_size_mm
  return [ox + (x + 0.5) * s, oy + (y + 0.5) * s, oz + (z + 0.5) * s]
}

/**
 * Начальное направление камеры, слегка скорректированное под реальные
 * пропорции заготовки — фиксированная изометрия [1,1,1] хороша для
 * кубовидных деталей, но для сильно вытянутых/плоских (напр. узкая
 * широкая плита, найдено визуальной проверкой на реальном fixture
 * 106×26×60мм) даёт ракурс, где силуэт частично схлопывается в узкий
 * "шеврон". Компонента направления по КАЖДОЙ оси растёт с протяжённостью
 * детали по этой оси (не наоборот — первая попытка с обратной
 * пропорциональностью и линейным весом давала камеру, направленную
 * СТРОГО вдоль самой длинной оси — плоский, "анфас" силуэт без объёма,
 * визуально хуже исходного шеврона). Квадратный корень вместо линейной
 * пропорции — мягкая, не резкая коррекция.
 */
function adaptiveCameraPosition(dims: [number, number, number]): [number, number, number] {
  const [dx, dy, dz] = dims
  const maxDim = Math.max(dx, dy, dz, 1)
  const wx = Math.sqrt(dx / maxDim)
  const wy = Math.sqrt(dy / maxDim)
  const wz = Math.sqrt(dz / maxDim)
  const norm = Math.sqrt(wx * wx + wy * wy + wz * wz) || 1
  const distance = 4.2
  return [(wx / norm) * distance, (wy / norm) * distance + 1.4, (wz / norm) * distance]
}

/** Текущий шаг анимации — единственный источник времени для всей сцены,
 * поднят в родительский компонент, чтобы StockVoxels и ToolCursor
 * двигались синхронно относительно одного и того же currentStep, а не
 * рассинхронизированных независимых таймеров. */
function useAnimationStep(totalSteps: number, playing: boolean, onProgress?: (step: number, total: number) => void) {
  const [currentStep, setCurrentStep] = useState(0)
  const startTimeRef = useRef<number | null>(null)

  useFrame(() => {
    if (!playing || totalSteps === 0) return
    if (startTimeRef.current === null) startTimeRef.current = performance.now()
    const elapsedMs = performance.now() - startTimeRef.current
    const progress = Math.min(1, elapsedMs / _ANIMATION_DURATION_MS)
    const step = Math.floor(progress * totalSteps)
    if (step !== currentStep) {
      setCurrentStep(step)
      onProgress?.(step, totalSteps)
    }
  })

  return currentStep
}

function StockVoxels({
  grid,
  events,
  currentStep,
}: {
  grid: VoxelGridSpec
  events: MaterialRemovalSimulation['events']
  currentStep: number
}) {
  const meshRef = useRef<InstancedMesh>(null)
  const lastAppliedStepRef = useRef(-1)

  const [nx, ny, nz] = grid.dims
  const voxelCount = nx * ny * nz

  const removalStepByVoxelIndex = useMemo(() => {
    const map = new Int32Array(voxelCount).fill(-1)
    for (const [x, y, z, step] of events) {
      const idx = x * ny * nz + y * nz + z
      map[idx] = step
    }
    return map
  }, [events, voxelCount, ny, nz])

  const positions = useMemo(() => {
    const arr = new Float32Array(voxelCount * 3)
    let i = 0
    for (let x = 0; x < nx; x++) {
      for (let y = 0; y < ny; y++) {
        for (let z = 0; z < nz; z++) {
          const [wx, wy, wz] = voxelWorldPosition(grid, x, y, z)
          arr[i * 3] = wx
          arr[i * 3 + 1] = wy
          arr[i * 3 + 2] = wz
          i++
        }
      }
    }
    return arr
  }, [grid, nx, ny, nz, voxelCount])

  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh) return
    for (let i = 0; i < voxelCount; i++) {
      _DUMMY.position.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2])
      _DUMMY.scale.setScalar(grid.voxel_size_mm * 0.96)
      _DUMMY.updateMatrix()
      mesh.setMatrixAt(i, _DUMMY.matrix)
    }
    mesh.instanceMatrix.needsUpdate = true
    lastAppliedStepRef.current = -1
  }, [positions, voxelCount, grid.voxel_size_mm])

  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh) return
    for (let i = 0; i < voxelCount; i++) {
      const removalStep = removalStepByVoxelIndex[i]
      if (removalStep > lastAppliedStepRef.current && removalStep <= currentStep) {
        _DUMMY.position.set(0, 0, 0)
        _DUMMY.scale.setScalar(0)
        _DUMMY.updateMatrix()
        mesh.setMatrixAt(i, _DUMMY.matrix)
      }
    }
    mesh.instanceMatrix.needsUpdate = true
    lastAppliedStepRef.current = currentStep
  }, [currentStep, removalStepByVoxelIndex, voxelCount])

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, voxelCount]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color={_STOCK_COLOR} transparent opacity={0.22} depthWrite={false} />
    </instancedMesh>
  )
}

function useStepMeshGeometry(stepFile: File): BufferGeometry | null {
  const [geometry, setGeometry] = useState<BufferGeometry | null>(null)

  useEffect(() => {
    let cancelled = false
    setGeometry(null)
    async function load() {
      const buffer = await fetchStepMesh(stepFile)
      if (cancelled || !buffer) return
      const loaded = new STLLoader().parse(buffer)
      loaded.computeVertexNormals()
      setGeometry(loaded)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [stepFile])

  return geometry
}

/** Целевая модель — реальная тесселяция STEP (не выдуманный контур),
 * тот же честный принцип, что уже применяется в PartViewer.tsx: если
 * pythonocc недоступен на этой машине, geometry остаётся null и целевая
 * модель просто не рендерится — не подменяется приближением. */
function TargetModel({ stepFile }: { stepFile: File }) {
  const geometry = useStepMeshGeometry(stepFile)
  if (!geometry) return null
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={_TARGET_COLOR} transparent opacity={0.55} depthWrite={false} />
    </mesh>
  )
}

/** Красный цилиндр-фреза — положение интерполируется вдоль moves
 * активной операции по currentStep (не-rapid move индексируется тем же
 * счётчиком шага, что voxel-симулятор использует для removed_at_step —
 * см. backend material_removal_simulator.py). */
function ToolCursor({ operations, currentStep, toolDiameterMm }: { operations: ToolpathOperation[]; currentStep: number; toolDiameterMm: number }) {
  const meshRef = useRef<Mesh>(null)

  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh) return

    const op = operations.find((o) => currentStep >= o.start_step && currentStep < o.end_step) ?? operations[operations.length - 1]
    if (!op) return

    const nonRapidMoves = op.moves.filter((m) => m.kind !== 'rapid')
    const localStep = Math.min(Math.max(currentStep - op.start_step, 0), nonRapidMoves.length - 1)
    const move = nonRapidMoves[localStep] ?? nonRapidMoves[nonRapidMoves.length - 1]
    if (!move) return

    mesh.position.set(move.x_mm, move.y_mm, move.z_mm)
  })

  return (
    <mesh ref={meshRef} rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[toolDiameterMm / 2, toolDiameterMm / 2, toolDiameterMm * 3, 16]} />
      <meshStandardMaterial color={_TOOL_COLOR} />
    </mesh>
  )
}

function Scene({ simulation, operations, stepModel, playing, onProgress }: ToolpathViewerProps) {
  const currentStep = useAnimationStep(simulation.total_steps, playing, onProgress)
  const activeToolDiameter = useMemo(() => {
    const op = operations.find((o) => currentStep >= o.start_step && currentStep < o.end_step) ?? operations[0]
    return op?.tool_diameter_mm ?? 6
  }, [operations, currentStep])

  // Bounds fit подгоняет камеру под фактические пропорции ВСЕЙ сцены
  // (заготовка+цель+фреза вместе, как одна группа) — все три источника
  // геометрии уже в одном мировом пространстве координат от backend,
  // поэтому центрирование применяется один раз к объединённому объёму,
  // не по отдельности к каждому (иначе они визуально "разъедутся").
  return (
    <Bounds fit observe margin={1.3}>
      <Center>
        <StockVoxels grid={simulation.grid} events={simulation.events} currentStep={currentStep} />
        <TargetModel stepFile={stepModel} />
        {operations.length > 0 && (
          <ToolCursor operations={operations} currentStep={currentStep} toolDiameterMm={activeToolDiameter} />
        )}
      </Center>
    </Bounds>
  )
}

export function ToolpathViewer({ simulation, operations, stepModel, playing, onProgress }: ToolpathViewerProps) {
  const cameraPosition = useMemo(() => adaptiveCameraPosition(simulation.grid.dims), [simulation.grid.dims])

  return (
    <div className={cn('relative h-full w-full overflow-hidden rounded-2xl border border-border bg-dark')}>
      <Canvas camera={{ position: cameraPosition, fov: 40 }}>
        <Suspense fallback={null}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[4, 6, 4]} intensity={1.1} />
          <Scene simulation={simulation} operations={operations} stepModel={stepModel} playing={playing} onProgress={onProgress} />
          <Environment preset="city" />
          <OrbitControls enablePan={false} enableZoom={false} enableRotate autoRotate autoRotateSpeed={1.4} />
        </Suspense>
      </Canvas>
      <div className="absolute bottom-3 left-3 flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider">
        <span className="text-sky-300/90">● заготовка</span>
        <span className="text-emerald-400/90">● целевая модель</span>
        <span className="text-red-400/90">● инструмент</span>
      </div>
    </div>
  )
}
