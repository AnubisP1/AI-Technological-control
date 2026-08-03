import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'

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

export function StatusPill({ dark = false }: { dark?: boolean }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
  })

  const state = isLoading ? 'loading' : isError ? 'error' : 'ok'

  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider',
        dark ? 'border-white/10 bg-white/5 text-white/60' : 'border-border bg-surface text-ink-dim'
      )}
    >
      <span
        className={
          'h-1.5 w-1.5 shrink-0 rounded-full ' +
          (state === 'ok'
            ? 'bg-emerald-500'
            : state === 'error'
              ? 'bg-red-500'
              : (dark ? 'bg-white/40' : 'bg-ink-dim') + ' animate-pulse')
        }
      />
      {state === 'ok' && data && (
        <span>
          backend online · CPU {data.cpu_thread_budget}/{data.cpu_count_total} потоков
        </span>
      )}
      {state === 'error' && <span className={dark ? 'text-red-400' : 'text-red-600'}>backend недоступен</span>}
      {state === 'loading' && <span>проверка backend…</span>}
    </div>
  )
}
