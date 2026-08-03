import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/components/layout/nav-items'

export function DockNav() {
  return (
    <nav
      aria-label="Modules"
      className="flex w-14 flex-none flex-col items-center gap-1 border-r border-border bg-surface pt-2.5"
    >
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          title={label}
          aria-label={label}
          className={({ isActive }) =>
            cn(
              'relative grid h-10 w-10 place-items-center rounded-lg text-fg-dim hover:bg-surface-2 hover:text-fg',
              isActive &&
                "bg-signal-100 text-signal-ink before:absolute before:-left-2 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-signal before:content-['']",
            )
          }
        >
          <Icon width={20} height={20} />
        </NavLink>
      ))}
    </nav>
  )
}
