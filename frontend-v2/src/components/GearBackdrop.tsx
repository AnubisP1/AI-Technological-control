import { Suspense, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF, Center, Environment } from '@react-three/drei'
import type { Group } from 'three'
import { cn } from '@/lib/utils'

/**
 * Готовая 3D-модель шестерни (Фаза 17, часть 5) — по прямому запросу
 * пользователя: декоративный фон на рабочих экранах и на главной
 * странице должен показывать узнаваемую механическую деталь (шестерню),
 * не абстрактный параллелепипед/куб. Источник — UI UX reference/gear.glb
 * (уже готовая авторская модель пользователя, не сгенерированная и не
 * тесселяция из STEP), скопирована в public/models/gear.glb.
 */
function GearMesh() {
  const { scene } = useGLTF('/models/gear.glb')
  const groupRef = useRef<Group>(null)

  useFrame((_, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += delta * 0.35
  })

  return (
    <Center>
      <group ref={groupRef}>
        <primitive object={scene} scale={2.2} />
      </group>
    </Center>
  )
}

export function GearBackdrop({
  className,
  transparentBackground = false,
}: {
  className?: string
  transparentBackground?: boolean
}) {
  return (
    <div className={cn('h-full w-full', className)}>
      <Canvas
        camera={{ position: [3, 2, 3], fov: 40 }}
        gl={{ alpha: transparentBackground }}
        style={transparentBackground ? { background: 'transparent' } : undefined}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[4, 6, 4]} intensity={1.2} />
          <GearMesh />
          {!transparentBackground && <Environment preset="city" />}
        </Suspense>
      </Canvas>
    </div>
  )
}

useGLTF.preload('/models/gear.glb')
