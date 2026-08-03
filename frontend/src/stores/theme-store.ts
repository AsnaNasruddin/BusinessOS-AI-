import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark'

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyThemeToDocument(theme: Theme) {
  document.documentElement.dataset.theme = theme
}

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

/**
 * BusinessOS's own light/dark preference — a real per-user setting that will
 * eventually live on the `User` row (see implementation plan, section 6) and
 * sync through the API instead of localStorage. Defaults to the OS preference
 * until the person explicitly picks a side, then remembers their choice.
 *
 * The `data-theme` attribute this writes to <html> is also set synchronously
 * by the inline script in index.html, so there's no flash of the wrong theme
 * before React hydrates.
 */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: systemTheme(),
      setTheme: (theme) => {
        applyThemeToDocument(theme)
        set({ theme })
      },
      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark'
        applyThemeToDocument(next)
        set({ theme: next })
      },
    }),
    {
      name: 'businessos-theme',
      onRehydrateStorage: () => (state) => {
        if (state) applyThemeToDocument(state.theme)
      },
    },
  ),
)
