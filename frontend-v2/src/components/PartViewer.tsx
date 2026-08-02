import { Suspense, useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, Center } from '@react-three/drei'
import { BoxGeometry } from 'three'

export interface PartViewerProps {
  lengthXMm: number
  lengthYMm: number
  lengthZMm: number
  partName?: string
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
  // Нормализуем в разумный масштаб сцены (метры почти всегда дают либо
  // микроскопическую, либо гигантскую сцену для деталей в десятки-сотни мм).
  const scale = 1 / 100
  const dims = useMemo(
    () => [lengthXMm * scale, lengthYMm * scale, lengthZMm * scale] as const,
    [lengthXMm, lengthYMm, lengthZMm]
  )

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

export function PartViewer(props: PartViewerProps) {
  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden border border-border bg-dark">
      <Canvas camera={{ position: [3, 2, 3], fov: 40 }} shadows>
        <Suspense fallback={null}>
          <ambientLight intensity={0.4} />
          <directionalLight position={[4, 6, 4]} intensity={1.2} castShadow />
          <ProxyBox {...props} />
          <Environment preset="city" />
          <OrbitControls enablePan={false} minDistance={1.5} maxDistance={8} />
        </Suspense>
      </Canvas>
      <div className="absolute top-3 left-3 font-mono text-[11px] uppercase tracking-wider text-white/60">
        {props.partName ?? 'STEP-модель'} · {props.lengthXMm}×{props.lengthYMm}×{props.lengthZMm} мм
      </div>
      <div className="absolute bottom-3 left-3 font-mono text-[10px] uppercase tracking-wider text-amber-300/80">
        параметрическая визуализация — не точная геометрия
      </div>
    </div>
  )
}
