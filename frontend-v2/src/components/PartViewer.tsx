import { Suspense, useEffect, useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, Center, Bounds } from '@react-three/drei'
import { BoxGeometry, BufferGeometry } from 'three'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { cn } from '@/lib/utils'
import { fetchStepMesh } from '@/lib/api'

export interface PartViewerProps {
  lengthXMm: number
  lengthYMm: number
  lengthZMm: number
  partName?: string
  autoRotate?: boolean
  hideOverlay?: boolean
  interactive?: boolean
  transparentBackground?: boolean
  /**
   * Исходный STEP-файл детали (Фаза 17, часть 5) — если передан,
   * PartViewer запрашивает у backend реальную тесселяцию (STL через
   * pythonocc-core, см. step_mesh_exporter.py) и показывает её вместо
   * параметрического прокси-бокса. Молча откатывается на прокси-бокс,
   * если backend не смог построить тесселяцию (pythonocc-core не
   * настроен на этой машине) — это ожидаемый fallback, не ошибка.
   */
  stepFile?: File | null
  /**
   * Альтернатива stepFile — путь к статически раздаваемому STEP-файлу
   * (напр. из public/, см. PageBackdrop.tsx) для случаев, когда у
   * компонента нет File-объекта из пользовательской загрузки, но есть
   * готовый файл на диске (декоративный фон на рабочих экранах —
   * реальные детали из КД для тестов/, скопированные в public/).
   */
  stepFileUrl?: string
}

/**
 * Параметрический прокси-вьюер (spike, Фаза 9).
 *
 * Backend не строит настоящую тесселяцию STEP в mesh (только bounding
 * box/число граней/цвета — см. RegexStepParser) — pythonocc-core
 * сознательно не подключается сейчас (см. dev/PLAN.md, согласовано с
 * пользователем). Эта модель — прямоугольный параллелепипед по
 * РЕАЛЬНЫМ размерам детали из STEP, не выдуманная и не точная
 * геометрия. UI обязан подписывать её как параметрическую визуализацию,
 * не как честный B-rep.
 */
function ProxyBox({ lengthXMm, lengthYMm, lengthZMm }: PartViewerProps) {
  // Нормализуем по наибольшему габариту к фиксированному размеру сцены
  // (не фиксированный делитель — детали в тестовых fixture варьируются
  // от ~20мм до ~2300мм, единый /100 либо тонет в камере, либо не влезает).
  const dims = useMemo(() => {
    const maxDim = Math.max(lengthXMm, lengthYMm, lengthZMm, 1)
    const scale = 2.4 / maxDim
    return [lengthXMm * scale, lengthYMm * scale, lengthZMm * scale] as const
  }, [lengthXMm, lengthYMm, lengthZMm])

  return (
    <Center>
      <mesh castShadow receiveShadow>
        <boxGeometry args={dims} />
        <meshStandardMaterial color="#7B8494" metalness={0.6} roughness={0.35} />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[new BoxGeometry(...dims)]} />
        <lineBasicMaterial color="#1B5CFF" />
      </lineSegments>
    </Center>
  )
}

/**
 * Реальная геометрия детали (Фаза 17, часть 5) — тесселяция STEP,
 * построенная backend через pythonocc-core и переданная как бинарный
 * STL. Center+Bounds центрируют и масштабируют модель в кадр так же,
 * как ProxyBox нормализует прокси-бокс по наибольшему габариту — модели
 * из реальных STEP-файлов приходят в исходном масштабе миллиметров
 * (десятки-тысячи единиц), не подогнанные под сцену заранее.
 */
function RealMesh({ geometry }: { geometry: BufferGeometry }) {
  return (
    <Bounds fit clip observe margin={1.3}>
      <Center>
        <mesh castShadow receiveShadow geometry={geometry}>
          <meshStandardMaterial color="#7B8494" metalness={0.6} roughness={0.35} />
        </mesh>
      </Center>
    </Bounds>
  )
}

function useStepMeshGeometry(
  stepFile: File | null | undefined,
  stepFileUrl: string | undefined
): BufferGeometry | null {
  const [geometry, setGeometry] = useState<BufferGeometry | null>(null)

  useEffect(() => {
    setGeometry(null)
    if (!stepFile && !stepFileUrl) return
    let cancelled = false

    async function load() {
      const file = stepFile ?? (await urlToFile(stepFileUrl!))
      if (!file) return
      const buffer = await fetchStepMesh(file)
      if (cancelled || !buffer) return
      const loaded = new STLLoader().parse(buffer)
      loaded.computeVertexNormals()
      setGeometry(loaded)
    }
    load()

    return () => {
      cancelled = true
    }
  }, [stepFile, stepFileUrl])

  return geometry
}

async function urlToFile(url: string): Promise<File | null> {
  const response = await fetch(url)
  if (!response.ok) return null
  const blob = await response.blob()
  return new File([blob], url.split('/').pop() ?? 'model.step')
}

export function PartViewer({
  autoRotate = false,
  hideOverlay = false,
  interactive = true,
  transparentBackground = false,
  stepFile,
  stepFileUrl,
  ...props
}: PartViewerProps) {
  const realGeometry = useStepMeshGeometry(stepFile, stepFileUrl)
  const isRealGeometry = realGeometry !== null

  return (
    <div
      className={cn(
        'relative w-full h-full overflow-hidden',
        transparentBackground ? '' : 'rounded-2xl border border-border bg-dark'
      )}
    >
      <Canvas
        camera={{ position: [3, 2, 3], fov: 40 }}
        shadows
        gl={{ alpha: transparentBackground }}
        style={transparentBackground ? { background: 'transparent' } : undefined}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.4} />
          <directionalLight position={[4, 6, 4]} intensity={1.2} castShadow />
          {isRealGeometry ? <RealMesh geometry={realGeometry} /> : <ProxyBox {...props} />}
          {!transparentBackground && <Environment preset="city" />}
          <OrbitControls
            enablePan={false}
            enableZoom={interactive}
            enableRotate={interactive}
            autoRotate={autoRotate}
            autoRotateSpeed={1.4}
            minDistance={1.5}
            maxDistance={8}
          />
        </Suspense>
      </Canvas>
      {!hideOverlay && (
        <>
          <div className="absolute top-3 left-3 font-mono text-[11px] uppercase tracking-wider text-white/60">
            {props.partName ?? 'STEP-модель'} · {props.lengthXMm}×{props.lengthYMm}×{props.lengthZMm} мм
          </div>
          <div
            className={cn(
              'absolute bottom-3 left-3 font-mono text-[10px] uppercase tracking-wider',
              isRealGeometry ? 'text-emerald-300/80' : 'text-amber-300/80'
            )}
          >
            {isRealGeometry ? 'точная геометрия (тесселяция OpenCASCADE)' : 'параметрическая визуализация — не точная геометрия'}
          </div>
        </>
      )}
    </div>
  )
}
