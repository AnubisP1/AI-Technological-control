import { ImagePlus } from 'lucide-react'
import { cn } from '@/lib/utils'

export function PhotoDropzone({
  label,
  file,
  onChange,
}: {
  label: string
  file: File | null
  onChange: (file: File | null) => void
}) {
  const previewUrl = file ? URL.createObjectURL(file) : null

  return (
    <label
      className={cn(
        'relative flex aspect-square cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden rounded-2xl border transition-colors',
        file ? 'border-border' : 'border-dashed border-border bg-muted/30 hover:border-brand/40'
      )}
    >
      {previewUrl ? (
        <img src={previewUrl} alt={label} className="h-full w-full object-cover" />
      ) : (
        <>
          <ImagePlus className="h-6 w-6 text-ink-dim" />
          <span className="px-4 text-center text-xs text-ink-dim">{label}</span>
        </>
      )}
      <input
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      <div className="absolute bottom-0 left-0 right-0 bg-dark/70 px-3 py-1.5 text-center text-[11px] text-white backdrop-blur-sm">
        {label}
      </div>
    </label>
  )
}
