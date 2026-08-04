import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, AlertTriangle, HelpCircle, Search, ClipboardCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/marketing/Section'
import { PageBackdrop } from '@/components/PageBackdrop'
import { ApprovalDialog } from '@/components/production/ApprovalDialog'
import { useWorkflow, type WorkflowInput } from '@/lib/workflow'
import type { KdReviewReport, RouteCard, MatchStatus, PrintRouteCardResponse, MaterialRecommendationOption } from '@/lib/api'

/**
 * Экран "Экспертиза соответствия НСИ" (Фаза 17, часть 2; Фаза 20 —
 * реестр для пластика + чтение уже готового результата анализа).
 *
 * Данные больше не запрашиваются повторно на этом экране — и для
 * металла (KdReviewReport/RouteCard), и для пластика (PrintRouteCardResponse
 * + выбранная рекомендация автоподбора) экран читает уже полученный на
 * "Анализ детали" результат из WorkflowProvider (см. lib/workflow.tsx).
 * Анализ выполняется один раз, не дважды.
 */

type RegistryStatus = 'ok' | 'not_ok' | 'partial' | 'unchecked'

interface RegistryRow {
  id: string
  registry: string
  requirement: string
  projectDoc: string
  status: RegistryStatus
  note: string
}

const STATUS_META: Record<RegistryStatus, { label: string; className: string; icon: typeof CheckCircle2 }> = {
  ok: { label: 'Соответствует', className: 'text-emerald-700 bg-emerald-50 border-emerald-200', icon: CheckCircle2 },
  not_ok: { label: 'Не соответствует', className: 'text-red-700 bg-red-50 border-red-200', icon: XCircle },
  partial: { label: 'Частично', className: 'text-amber-700 bg-amber-50 border-amber-200', icon: AlertTriangle },
  unchecked: { label: 'Не проверяется', className: 'text-ink-dim bg-muted border-border', icon: HelpCircle },
}

const MATCH_TO_REGISTRY: Record<MatchStatus, RegistryStatus> = {
  matched: 'ok',
  partial_match: 'partial',
  not_found: 'not_ok',
}

function buildMetalRegistryRows(review: KdReviewReport, routeCard: RouteCard): RegistryRow[] {
  const rows: RegistryRow[] = []

  if (review.material_check) {
    const mc = review.material_check
    rows.push({
      id: 'material',
      registry: 'НСИ · Материалы',
      requirement: 'Материал заготовки должен присутствовать в справочнике НСИ',
      projectDoc: mc.material_from_drawing || '—',
      status: MATCH_TO_REGISTRY[mc.status],
      note: mc.note || '—',
    })
  }

  if (review.blank_check) {
    const bc = review.blank_check
    rows.push({
      id: 'blank',
      registry: 'НСИ · Заготовки',
      requirement: 'Типоразмер заготовки должен присутствовать в справочнике НСИ',
      projectDoc: bc.blank_from_drawing || '—',
      status: MATCH_TO_REGISTRY[bc.status],
      note: bc.note || '—',
    })
  }

  review.technical_requirement_checks.forEach((tt) => {
    rows.push({
      id: `tt-${tt.number}`,
      registry: 'Технические требования',
      requirement: `п.${tt.number}: ${tt.text}`,
      projectDoc: tt.category ? `категория: ${tt.category}` : 'категория не распознана',
      status: tt.is_recognized ? 'ok' : 'unchecked',
      note: tt.is_recognized ? '—' : 'формулировка не сопоставлена с известной категорией ТТ',
    })
  })

  routeCard.rows.forEach((row, i) => {
    const [opNo, opName, , , , , equipment] = row
    rows.push({
      id: `op-${opNo}-${i}`,
      registry: 'НСИ · Оборудование',
      requirement: `Операция ${opNo}: для «${opName}» должно быть подобрано оборудование из справочника`,
      projectDoc: equipment || '—',
      status: equipment && equipment !== 'не подобрано' ? 'ok' : 'not_ok',
      note:
        equipment && equipment !== 'не подобрано'
          ? '—'
          : 'подходящая модель станка не найдена в справочнике по текущим правилам совместимости',
    })
  })

  return rows
}

function buildPlasticRegistryRows(
  printCards: PrintRouteCardResponse,
  selectedOption: MaterialRecommendationOption
): RegistryRow[] {
  const rows: RegistryRow[] = []
  const profile = printCards.material_print_profile

  rows.push({
    id: 'material-recommendation',
    registry: 'НСИ · Автоподбор материала',
    requirement: 'Для класса применения детали должна быть рекомендация материала в справочнике НСИ',
    projectDoc: `${selectedOption.material_group_name} · ${selectedOption.am_technology_name}`,
    status: 'ok',
    note: `${selectedOption.source_title} (${selectedOption.source_reliability === 'high' ? 'высокая' : selectedOption.source_reliability === 'medium' ? 'средняя' : 'низкая'} надёжность источника)`,
  })

  rows.push({
    id: 'printer',
    registry: 'НСИ · Оборудование',
    requirement: 'Для подобранного материала должна быть подобрана модель принтера из справочника',
    projectDoc: printCards.process_card.row[1] || '—',
    status: printCards.process_card.row[1] && printCards.process_card.row[1] !== 'не подобран' ? 'ok' : 'not_ok',
    note:
      printCards.process_card.row[1] && printCards.process_card.row[1] !== 'не подобран'
        ? '—'
        : 'подходящая модель принтера не найдена в справочнике по текущим правилам совместимости',
  })

  if (profile) {
    const tempNote =
      profile.print_temp_min_c != null && profile.print_temp_max_c != null
        ? `сопло ${profile.print_temp_min_c}–${profile.print_temp_max_c}°C${profile.bed_temp_c != null ? `, стол ${profile.bed_temp_c}°C` : ''}`
        : 'температурный режим не применим для этого типа технологии (не FDM-филамент)'
    rows.push({
      id: 'print-temperature',
      registry: 'НСИ · Параметры печати',
      requirement: 'Температурный режим печати конкретной марки материала (для установки на принтере/слайсере)',
      projectDoc: profile.trade_name,
      status: 'ok',
      note: tempNote,
    })

    if (profile.requires_heated_chamber || profile.requires_dry_storage) {
      const requirements = [
        profile.requires_heated_chamber && 'подогреваемая камера печати',
        profile.requires_dry_storage && 'сухое хранение материала (гигроскопичен)',
      ]
        .filter(Boolean)
        .join('; ')
      rows.push({
        id: 'print-requirements',
        registry: 'НСИ · Параметры печати',
        requirement: 'Особые требования к оборудованию/хранению материала',
        projectDoc: profile.trade_name,
        status: 'partial',
        note: requirements,
      })
    }
  } else {
    rows.push({
      id: 'print-temperature',
      registry: 'НСИ · Параметры печати',
      requirement: 'Температурный режим печати конкретной марки материала',
      projectDoc: selectedOption.material_group_name,
      status: 'not_ok',
      note: 'В справочнике НСИ нет конкретной марки материала для этой группы — параметры печати не могут быть указаны',
    })
  }

  if (selectedOption.min_infill_percent != null || selectedOption.recommended_wall_count != null) {
    rows.push({
      id: 'infill',
      registry: 'НСИ · Параметры печати',
      requirement: 'Заполнение и число стенок по рекомендации для класса применения детали',
      projectDoc: selectedOption.material_group_name,
      status: 'ok',
      note: [
        selectedOption.min_infill_percent != null ? `мин. заполнение ${selectedOption.min_infill_percent}%` : null,
        selectedOption.recommended_wall_count != null ? `стенок: ${selectedOption.recommended_wall_count}` : null,
        selectedOption.orientation_note,
      ]
        .filter(Boolean)
        .join('; '),
    })
  }

  const qs = printCards.process_card.quality_standard
  if (qs) {
    rows.push({
      id: 'quality-standard',
      registry: 'НСИ · Допуски технологии',
      requirement: 'Допуски и шероховатость поверхности по технологии печати',
      projectDoc: `допуск ${qs.tolerance_mm}, мин. толщина стенки ${qs.min_wall_thickness_mm} мм`,
      status: 'ok',
      note: qs.source_note,
    })
  }

  printCards.warnings.forEach((w, i) => {
    rows.push({
      id: `warning-${i}`,
      registry: 'НСИ · Замечания автоподбора',
      requirement: 'Автоподбор техпроцесса печати не должен давать замечаний',
      projectDoc: '—',
      status: 'not_ok',
      note: w,
    })
  })

  return rows
}

function buildRegistryRows(pendingInput: WorkflowInput | null): RegistryRow[] {
  if (!pendingInput) return []
  if (pendingInput.kind === 'metal') {
    return buildMetalRegistryRows(pendingInput.review, pendingInput.routeCard)
  }
  return buildPlasticRegistryRows(pendingInput.printCards, pendingInput.selectedOption)
}

function StatCard({ label, count, total, className }: { label: string; count: number; total: number; className: string }) {
  const percent = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div className={`rounded-xl border p-4 ${className}`}>
      <div className="text-xs font-medium">{label}</div>
      <div className="mt-1 text-3xl font-bold tabular-nums">{count}</div>
      <div className="mt-0.5 text-[11px] opacity-70">{percent}% от проверенных</div>
    </div>
  )
}

export function NsiExpertisePage() {
  const navigate = useNavigate()
  const { pendingInput, acknowledgeNsiExpertise, markApproved } = useWorkflow()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<RegistryStatus | 'all'>('all')
  const [registryFilter, setRegistryFilter] = useState<string | 'all'>('all')
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false)

  function handleApproved() {
    acknowledgeNsiExpertise()
    markApproved()
    navigate('/app/production')
  }

  const rows = useMemo(() => buildRegistryRows(pendingInput), [pendingInput])
  const registries = useMemo(() => Array.from(new Set(rows.map((r) => r.registry))), [rows])

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      if (statusFilter !== 'all' && row.status !== statusFilter) return false
      if (registryFilter !== 'all' && row.registry !== registryFilter) return false
      if (search) {
        const haystack = `${row.requirement} ${row.projectDoc} ${row.note}`.toLowerCase()
        if (!haystack.includes(search.toLowerCase())) return false
      }
      return true
    })
  }, [rows, statusFilter, registryFilter, search])

  const counts = useMemo(() => {
    const c: Record<RegistryStatus, number> = { ok: 0, not_ok: 0, partial: 0, unchecked: 0 }
    rows.forEach((r) => c[r.status]++)
    return c
  }, [rows])

  const hasData = rows.length > 0

  return (
    <Container className="max-w-6xl py-10">
      <PageBackdrop compact />
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Экспертиза соответствия НСИ</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-dim">
          {pendingInput?.kind === 'plastic'
            ? 'Проверка подобранного автоподбором материала, технологии печати, температурного режима и допусков по базе нормативно-справочной информации проекта.'
            : 'Проверка материала, заготовки, технических требований и подобранного оборудования детали по базе нормативно-справочной информации проекта — те же данные, что и в отчёте Модуля 1.2 и маршрутной карте, представленные как реестр требований с фильтрами.'}
        </p>
      </div>

      {!pendingInput && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Деталь не загружена. Сначала пройдите «Анализ детали» — результат экспертизы появится здесь
          автоматически.
        </div>
      )}

      {hasData && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Соответствует" count={counts.ok} total={rows.length} className="border-emerald-200 bg-emerald-50 text-emerald-800" />
            <StatCard label="Не соответствует" count={counts.not_ok} total={rows.length} className="border-red-200 bg-red-50 text-red-800" />
            <StatCard label="Частично" count={counts.partial} total={rows.length} className="border-amber-200 bg-amber-50 text-amber-800" />
            <StatCard label="Не проверяется" count={counts.unchecked} total={rows.length} className="border-border bg-muted text-ink-dim" />
          </div>

          <div className="mb-4 grid grid-cols-1 gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-3">
            <label className="flex items-center gap-2 rounded-lg border border-border bg-bg px-3 py-1.5 text-sm">
              <Search className="h-3.5 w-3.5 text-ink-dim" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Поиск по требованию, документации, замечанию"
                className="w-full bg-transparent outline-none placeholder:text-ink-dim"
              />
            </label>
            <select
              value={registryFilter}
              onChange={(e) => setRegistryFilter(e.target.value)}
              className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm"
            >
              <option value="all">Все реестры</option>
              {registries.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as RegistryStatus | 'all')}
              className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm"
            >
              <option value="all">Все статусы</option>
              {(Object.keys(STATUS_META) as RegistryStatus[]).map((s) => (
                <option key={s} value={s}>
                  {STATUS_META[s].label}
                </option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/60 text-left text-xs uppercase tracking-wide text-ink-dim">
                  <th className="px-3 py-2 font-medium">Реестр</th>
                  <th className="px-3 py-2 font-medium">Требование</th>
                  <th className="px-3 py-2 font-medium">Проектная документация</th>
                  <th className="px-3 py-2 font-medium">Статус</th>
                  <th className="px-3 py-2 font-medium">Замечание</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => {
                  const meta = STATUS_META[row.status]
                  return (
                    <tr key={row.id} className="border-t border-border align-top">
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-ink-dim">{row.registry}</td>
                      <td className="px-3 py-2.5 text-ink">{row.requirement}</td>
                      <td className="px-3 py-2.5 font-mono text-xs text-ink">{row.projectDoc}</td>
                      <td className="whitespace-nowrap px-3 py-2.5">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${meta.className}`}
                        >
                          <meta.icon className="h-3 w-3" />
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-ink-dim">{row.note}</td>
                    </tr>
                  )
                })}
                {filteredRows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-sm text-ink-dim">
                      Нет строк, соответствующих текущим фильтрам.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-6 rounded-2xl border border-border bg-surface p-6">
            {counts.not_ok > 0 && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                В реестре есть {counts.not_ok} несоответствующих пункта — проверьте их перед передачей
                на согласование главному технологу.
              </div>
            )}
            <p className="mb-3 text-sm text-ink-dim">
              Экспертиза проведена. Главный технолог может согласовать комплект технологической
              документации прямо здесь.
            </p>
            <Button onClick={() => setApprovalDialogOpen(true)}>
              <ClipboardCheck className="h-4 w-4" />
              Перейти к согласованию
            </Button>
          </div>
        </motion.div>
      )}

      <ApprovalDialog open={approvalDialogOpen} onOpenChange={setApprovalDialogOpen} onApproved={handleApproved} />
    </Container>
  )
}
