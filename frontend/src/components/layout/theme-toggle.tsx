import { useThemeStore } from '@/stores/theme-store'
import { MoonIcon, SunIcon } from '@/components/layout/icons'

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggleTheme)
  const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className="grid h-[30px] w-[30px] flex-none place-items-center rounded-md border border-transparent text-fg-dim hover:border-border hover:bg-surface-2 hover:text-fg"
    >
      {theme === 'dark' ? <SunIcon width={16} height={16} /> : <MoonIcon width={16} height={16} />}
    </button>
  )
}
