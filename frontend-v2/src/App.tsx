import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { PartViewer } from '@/components/PartViewer'

interface HealthResponse {
  status: string
  cpu_thread_budget: number
  cpu_count_total: number
}

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error('Backend недоступен')
  return response.json()
}

function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  return (
    <div className="min-h-svh bg-bg text-ink flex flex-col items-center justify-center gap-6 p-10">
      <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-dim">
        <span className="h-2 w-2 rounded-full bg-accent" />
        AI-Технолог · Фаза 9 · фундамент
      </div>
      <h1 className="text-4xl font-bold tracking-tight text-center max-w-xl text-balance">
        Новый фронтенд поднят: Vite + React + TypeScript + Tailwind + shadcn/ui
      </h1>
      <div className="rounded-2xl border border-border bg-surface px-6 py-4 font-mono text-sm">
        {isLoading && 'Проверка backend…'}
        {isError && <span className="text-red-600">backend недоступен (запустите uvicorn на :8000)</span>}
        {data && (
          <span>
            backend: {data.status} · CPU-бюджет {data.cpu_thread_budget}/{data.cpu_count_total} потоков
          </span>
        )}
      </div>
      <Button>shadcn/ui Button работает</Button>
      <div className="w-[420px] h-[320px]">
        <PartViewer
          partName="SQUID RUS 2_крышка 2"
          lengthXMm={109.053}
          lengthYMm={98.383}
          lengthZMm={196.766}
        />
      </div>
    </div>
  )
}

export default App
