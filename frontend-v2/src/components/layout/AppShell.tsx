import { type ReactNode } from 'react'
import { NavLink } from 'react-router'
import {
  ScanSearch,
  Factory,
  ShieldCheck,
  Network,
  Sparkles,
  Home,
  ClipboardCheck,
  LayoutDashboard,
  FileText,
} from 'lucide-react'
import { StatusPill } from '@/components/layout/StatusPill'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/app/overview', label: 'Обзор', icon: LayoutDashboard },
  { to: '/app/analysis', label: 'Анализ детали', icon: ScanSearch },
  { to: '/app/nsi-expertise', label: 'Экспертиза НСИ', icon: ClipboardCheck },
  { to: '/app/production', label: 'Производство', icon: Factory },
  { to: '/app/quality', label: 'Контроль качества', icon: ShieldCheck },
  { to: '/app/digital-twin', label: 'Цифровой двойник', icon: Network },
  { to: '/app/documents', label: 'Документы', icon: FileText },
] as const

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-svh bg-bg text-ink flex">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-border bg-dark text-white/90">
        <NavLink
          to="/"
          className="flex items-center gap-2 px-5 py-5 text-sm font-semibold tracking-tight"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand text-white">
            <Sparkles className="h-4 w-4" />
          </span>
          AI-Технолог
        </NavLink>
        <nav className="flex-1 px-3 py-2 flex flex-col gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/60 transition-colors hover:bg-white/5 hover:text-white',
                isActive && 'bg-white/10 text-white'
              )
            }
          >
            <Home className="h-4 w-4" />
            Главная
          </NavLink>
          <div className="mt-3 mb-1 px-3 text-[11px] font-mono uppercase tracking-widest text-white/30">
            Модули
          </div>
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/60 transition-colors hover:bg-white/5 hover:text-white',
                  isActive && 'bg-white/10 text-white'
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-[11px] font-mono uppercase tracking-widest text-white/25">
          БПЛА · офлайн-контур
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-5">
          <div className="md:hidden font-semibold tracking-tight">AI-Технолог</div>
          <div className="hidden md:block" />
          <StatusPill />
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
