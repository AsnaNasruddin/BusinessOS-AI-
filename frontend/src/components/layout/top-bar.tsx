import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { NAV_ITEMS } from '@/components/layout/nav-items'
import { BrandMark, ChevronDownIcon } from '@/components/layout/icons'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { useAuthStore } from '@/stores/auth-store'

function initials(fullName: string | undefined): string {
  if (!fullName) return ''
  const parts = fullName.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase()
}

export function TopBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const active = NAV_ITEMS.find((item) => location.pathname.startsWith(item.to))

  const user = useAuthStore((state) => state.user)
  const memberships = useAuthStore((state) => state.memberships)
  const currentOrgId = useAuthStore((state) => state.currentOrgId)
  const setCurrentOrg = useAuthStore((state) => state.setCurrentOrg)
  const logout = useAuthStore((state) => state.logout)

  const currentMembership = memberships.find((m) => m.orgId === currentOrgId)

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function onClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [menuOpen])

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

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
        <div ref={menuRef} className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-1.5 rounded-md border border-transparent px-2.5 py-1.5 text-[13px] font-medium hover:border-border hover:bg-surface-2"
          >
            {currentMembership?.orgName ?? 'Select org'}
            <ChevronDownIcon />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-[calc(100%+6px)] z-20 w-56 rounded-md border border-border bg-surface py-1 shadow-lg">
              <div className="px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-fg-faint">
                Organizations
              </div>
              {memberships.map((m) => (
                <button
                  key={m.orgId}
                  onClick={() => {
                    setCurrentOrg(m.orgId)
                    setMenuOpen(false)
                  }}
                  className="flex w-full items-center justify-between px-3 py-1.5 text-left text-[13px] hover:bg-surface-2"
                >
                  <span>{m.orgName}</span>
                  {m.orgId === currentOrgId && <span className="text-signal-ink">•</span>}
                </button>
              ))}
              <div className="my-1 border-t border-border" />
              <button
                onClick={handleLogout}
                className="w-full px-3 py-1.5 text-left text-[13px] text-critical-text hover:bg-critical-bg"
              >
                Log out
              </button>
            </div>
          )}
        </div>

        <ThemeToggle />

        <div className="grid h-[26px] w-[26px] flex-none place-items-center rounded-md bg-agent text-[11px] font-semibold text-white">
          {user ? initials(user.fullName) : ''}
        </div>
      </div>
    </header>
  )
}
