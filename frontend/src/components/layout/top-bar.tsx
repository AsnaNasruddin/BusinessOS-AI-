import { useLocation } from 'react-router-dom'
import { currentOrg, currentUser } from '@/lib/seed-data'
import { NAV_ITEMS } from '@/components/layout/nav-items'
import { BrandMark, ChevronDownIcon } from '@/components/layout/icons'
import { ThemeToggle } from '@/components/layout/theme-toggle'

export function TopBar() {
  const location = useLocation()
  const active = NAV_ITEMS.find((item) => location.pathname.startsWith(item.to))

  return (
    <header className="flex h-[46px] flex-none items-center justify-between gap-4 border-b border-border bg-surface px-4">
      <div className="flex flex-none items-center gap-2.5">
        <BrandMark />
        <span className="whitespace-nowrap text-sm font-semibold tracking-tight">BusinessOS</span>
        <span className="h-4 w-px flex-none bg-border" />
        <span className="whitespace-nowrap text-[13px] font-medium text-fg-dim">
          {active?.label ?? ''}
        </span>
      </div>

      <div className="flex min-w-0 flex-1 items-center justify-center gap-2.5 overflow-hidden whitespace-nowrap font-mono text-xs text-fg-dim">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-2.5 py-0.5 text-fg">
          <i className="h-1.5 w-1.5 flex-none rounded-full bg-good" />
          Local — llama3.1:8b
        </span>
        <span>3 running</span>
        <span className="text-fg-faint">·</span>
        <span>12,480 tok/min</span>
        <span className="text-fg-faint">·</span>
        <span>$0.00 today</span>
      </div>

      <div className="flex flex-none items-center gap-2.5">
        <button className="flex items-center gap-1.5 rounded-md border border-transparent px-2.5 py-1.5 text-[13px] font-medium hover:border-border hover:bg-surface-2">
          {currentOrg.name}
          <ChevronDownIcon />
        </button>
        <ThemeToggle />
        <div className="grid h-[26px] w-[26px] flex-none place-items-center rounded-md bg-agent text-[11px] font-semibold text-white">
          {currentUser.initials}
        </div>
      </div>
    </header>
  )
}
