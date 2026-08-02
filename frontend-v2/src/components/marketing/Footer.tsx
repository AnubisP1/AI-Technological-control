import { Container } from '@/components/marketing/Section'

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface py-10">
      <Container className="flex flex-col items-center gap-6 text-center md:flex-row md:justify-between md:text-left">
        <div>
          <div className="text-sm font-semibold tracking-tight text-ink">AI-Технолог</div>
          <p className="mt-1 max-w-sm text-xs text-ink-dim">
            Локальная офлайн-система анализа конструкторской документации и генерации
            технологической документации для производства деталей БПЛА.
          </p>
        </div>
        <div className="flex flex-col items-center gap-2 md:items-end">
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">
            Разработано при поддержке
          </span>
          <img
            src="/mai-logo.svg"
            alt="Московский авиационный институт"
            className="h-10 rounded-md bg-white px-2 py-1"
          />
        </div>
      </Container>
    </footer>
  )
}
