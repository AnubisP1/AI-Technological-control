import { useQuery } from '@tanstack/react-query'
import { UploadCloud, FileText, Box } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { fetchPartApplicationClasses } from '@/lib/api'

export type MaterialKind = 'metal' | 'plastic'

function FileField({
  label,
  accept,
  file,
  onChange,
  icon: Icon,
  optional = false,
  hint,
}: {
  label: string
  accept?: string
  file: File | null
  onChange: (file: File | null) => void
  icon: typeof FileText
  /** Пометка "необязательно" — чтобы было видно, что анализ запустится и без этого файла. */
  optional?: boolean
  hint?: string
}) {
  return (
    <label
      className={cn(
        'flex min-w-0 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-6 text-center transition-colors',
        file ? 'border-brand/40 bg-brand/[0.03]' : 'border-border bg-surface hover:border-brand/30'
      )}
    >
      <Icon className={cn('h-5 w-5 shrink-0', file ? 'text-brand' : 'text-ink-dim')} />
      <span className="text-xs font-medium text-ink">
        {label}
        {optional ? <span className="ml-1 font-normal text-ink-dim">— необязательно</span> : null}
      </span>
      <span className="max-w-full truncate text-[11px] text-ink-dim">
        {file ? file.name : 'нажмите, чтобы выбрать файл'}
      </span>
      {hint && !file ? (
        <span className="max-w-full text-[11px] leading-snug text-ink-dim">{hint}</span>
      ) : null}
      <input
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
    </label>
  )
}

export function UploadPanel({
  materialKind,
  onMaterialKindChange,
  drawing,
  onDrawingChange,
  stepModel,
  onStepModelChange,
  partApplicationClassCode,
  onPartApplicationClassChange,
  busy,
  canAnalyze,
  onAnalyze,
}: {
  materialKind: MaterialKind
  onMaterialKindChange: (kind: MaterialKind) => void
  drawing: File | null
  onDrawingChange: (file: File | null) => void
  stepModel: File | null
  onStepModelChange: (file: File | null) => void
  partApplicationClassCode: string
  onPartApplicationClassChange: (code: string) => void
  busy: boolean
  canAnalyze: boolean
  onAnalyze: () => void
}) {
  const classesQuery = useQuery({
    queryKey: ['part-application-classes'],
    queryFn: fetchPartApplicationClasses,
    enabled: materialKind === 'plastic',
  })

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-5 flex items-center gap-1 rounded-lg bg-muted p-1 text-sm">
        {(
          [
            ['metal', 'Металл'],
            ['plastic', 'Пластик'],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => onMaterialKindChange(value)}
            className={cn(
              'flex-1 rounded-md px-3 py-1.5 font-medium transition-colors',
              materialKind === value ? 'bg-surface text-ink shadow-sm' : 'text-ink-dim'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {materialKind === 'metal' ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <FileField
            label="Чертёж (PDF)"
            accept="application/pdf"
            file={drawing}
            onChange={onDrawingChange}
            icon={FileText}
          />
          <FileField
            label="STEP-модель"
            file={stepModel}
            onChange={onStepModelChange}
            icon={Box}
            optional
            hint="Без модели доступны оценка КД, сверка с НСИ, проверка по ГОСТ и маршрутная карта. Расчёт УП на «Производстве» требует STEP."
          />
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <FileField label="STEP-модель" file={stepModel} onChange={onStepModelChange} icon={Box} />
          <div>
            <div className="mb-2 font-mono text-xs uppercase tracking-wider text-ink-dim">
              Класс применения детали
            </div>
            <div className="flex flex-wrap gap-2">
              {classesQuery.data?.map((cls) => (
                <button
                  key={cls.code}
                  type="button"
                  title={cls.description ?? undefined}
                  onClick={() => onPartApplicationClassChange(cls.code)}
                  className={cn(
                    'rounded-lg border px-3 py-1.5 text-xs transition-colors',
                    partApplicationClassCode === cls.code
                      ? 'border-brand bg-brand text-white'
                      : 'border-border bg-surface text-ink-dim hover:border-brand/40'
                  )}
                >
                  {cls.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <Button
        className="mt-5 h-10 w-full text-sm"
        disabled={!canAnalyze || busy}
        onClick={onAnalyze}
      >
        <UploadCloud className="h-4 w-4" />
        {busy ? 'Обработка…' : 'Проанализировать и сгенерировать документацию'}
      </Button>
    </div>
  )
}
