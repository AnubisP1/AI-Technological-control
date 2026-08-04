import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Sparkles, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  fetchOperatingConditions,
  fetchMaterialRecommendations,
  type MaterialRecommendationOption,
} from '@/lib/api'

const RELIABILITY_LABEL: Record<string, string> = {
  high: 'высокая надёжность источника',
  medium: 'средняя надёжность источника',
  low: 'низкая надёжность источника',
}

function OptionCard({ option, hero }: { option: MaterialRecommendationOption; hero?: boolean }) {
  return (
    <div
      className={cn(
        'rounded-2xl border p-5',
        hero ? 'border-brand/30 bg-brand/[0.04]' : 'border-border bg-surface'
      )}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {hero && <Sparkles className="h-4 w-4 shrink-0 text-brand" />}
          <span className="text-base font-semibold text-ink">
            {option.material_group_name}
          </span>
          <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] text-ink-dim">
            {option.am_technology_name}
          </span>
        </div>
        <span className="font-mono text-[11px] uppercase tracking-wider text-ink-dim">
          приоритет {option.priority}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-ink-dim">{option.rationale}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-ink-dim">
        <span className="rounded-full border border-border px-2 py-0.5">
          {RELIABILITY_LABEL[option.source_reliability] ?? option.source_reliability}
        </span>
        <span>· {option.source_title}</span>
      </div>
      {(option.min_infill_percent || option.recommended_wall_count || option.orientation_note) && (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-border pt-3 text-xs">
          {option.min_infill_percent != null && (
            <>
              <dt className="text-ink-dim">Мин. заполнение</dt>
              <dd className="text-ink">{option.min_infill_percent}%</dd>
            </>
          )}
          {option.recommended_wall_count != null && (
            <>
              <dt className="text-ink-dim">Рекомендуемое число стенок</dt>
              <dd className="text-ink">{option.recommended_wall_count}</dd>
            </>
          )}
          {option.orientation_note && (
            <>
              <dt className="col-span-2 text-ink-dim">Ориентация печати</dt>
              <dd className="col-span-2 text-ink">{option.orientation_note}</dd>
            </>
          )}
        </dl>
      )}
    </div>
  )
}

export function MaterialRecommendation({
  partApplicationClassCode,
  onSelect,
}: {
  partApplicationClassCode: string
  onSelect: (option: MaterialRecommendationOption | null) => void
}) {
  const [selectedConditions, setSelectedConditions] = useState<string[]>([])
  const [altOpen, setAltOpen] = useState(false)

  const conditionsQuery = useQuery({
    queryKey: ['operating-conditions', partApplicationClassCode],
    queryFn: () => fetchOperatingConditions(partApplicationClassCode),
  })

  const recommendationQuery = useQuery({
    queryKey: ['material-recommendations', partApplicationClassCode, selectedConditions],
    queryFn: () =>
      fetchMaterialRecommendations({
        partApplicationClassCode,
        operatingConditionCodes: selectedConditions,
      }),
  })

  const top = recommendationQuery.data?.options[0] ?? null
  const alternatives = recommendationQuery.data?.options.slice(1) ?? []

  useEffect(() => {
    onSelect(top)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [top?.material_group_code, top?.am_technology_code])

  function toggleCondition(code: string) {
    setSelectedConditions((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {conditionsQuery.data && conditionsQuery.data.length > 0 && (
        <div>
          <div className="mb-2 font-mono text-xs uppercase tracking-wider text-ink-dim">
            Условия эксплуатации (опционально — уточняет рекомендацию)
          </div>
          <div className="flex flex-wrap gap-2">
            {conditionsQuery.data.map((condition) => (
              <button
                key={condition.code}
                type="button"
                onClick={() => toggleCondition(condition.code)}
                className={cn(
                  'rounded-full border px-3 py-1.5 text-xs transition-colors',
                  selectedConditions.includes(condition.code)
                    ? 'border-brand bg-brand text-white'
                    : 'border-border bg-surface text-ink-dim hover:border-brand/40'
                )}
              >
                {condition.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {recommendationQuery.isLoading && (
        <div className="rounded-2xl border border-border bg-surface p-5 text-sm text-ink-dim">
          Подбираем материал…
        </div>
      )}

      {recommendationQuery.data && recommendationQuery.data.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
          {recommendationQuery.data.warnings.map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </div>
      )}

      {top && (
        <motion.div
          key={`${top.material_group_code}-${top.am_technology_code}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <OptionCard option={top} hero />
        </motion.div>
      )}

      {alternatives.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setAltOpen((o) => !o)}
            className="flex items-center gap-1.5 text-xs font-medium text-ink-dim hover:text-ink"
          >
            <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', altOpen && 'rotate-180')} />
            {altOpen ? 'скрыть' : 'показать'} альтернативы ({alternatives.length})
          </button>
          {altOpen && (
            <div className="mt-3 flex flex-col gap-3">
              {alternatives.map((option) => (
                <OptionCard key={`${option.material_group_code}-${option.am_technology_code}`} option={option} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
