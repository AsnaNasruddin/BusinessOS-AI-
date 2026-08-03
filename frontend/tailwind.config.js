/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        'surface-2': 'var(--surface-2)',
        'surface-3': 'var(--surface-3)',
        border: 'var(--border)',
        fg: 'var(--text)',
        'fg-dim': 'var(--text-dim)',
        'fg-faint': 'var(--text-faint)',

        signal: 'var(--signal)',
        'signal-ink': 'var(--signal-ink)',
        'signal-100': 'var(--signal-100)',
        'signal-solid': 'var(--signal-solid)',
        'signal-solid-hover': 'var(--signal-solid-hover)',

        good: 'var(--good)',
        'good-bg': 'var(--good-bg)',
        'good-text': 'var(--good-text)',
        warn: 'var(--warn)',
        'warn-bg': 'var(--warn-bg)',
        'warn-text': 'var(--warn-text)',
        critical: 'var(--critical)',
        'critical-bg': 'var(--critical-bg)',
        'critical-text': 'var(--critical-text)',
        agent: 'var(--agent)',
        'agent-bg': 'var(--agent-bg)',
        'agent-text': 'var(--agent-text)',
        tool: 'var(--tool)',
        'tool-bg': 'var(--tool-bg)',
        'tool-text': 'var(--tool-text)',
      },
      fontFamily: {
        sans: ['"Plex Sans Var"', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: 'var(--shadow)',
      },
      borderRadius: {
        DEFAULT: '6px',
      },
    },
  },
  darkMode: ['selector', '[data-theme="dark"]'],
  plugins: [require('tailwindcss-animate')],
}
