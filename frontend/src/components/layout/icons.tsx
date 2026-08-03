import type { SVGProps } from 'react'

/** Small, stroke-based icon set — hand-drawn to match the rest of the system rather than pulled from a generic icon pack. */

export function BrandMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" width={18} height={18} aria-hidden {...props}>
      <rect x="1" y="1" width="8" height="8" rx="1.5" fill="var(--signal)" />
      <rect x="11" y="1" width="8" height="8" rx="1.5" fill="var(--agent)" />
      <rect x="1" y="11" width="8" height="8" rx="1.5" fill="var(--tool)" />
      <rect x="11" y="11" width="8" height="8" rx="1.5" fill="var(--border)" />
    </svg>
  )
}

export function ChevronDownIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 12 12" width={12} height={12} fill="none" aria-hidden {...props}>
      <path
        d="M3 4.5L6 7.5L9 4.5"
        stroke="currentColor"
        strokeWidth={1.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function SunIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth={1.6} />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
    </svg>
  )
}

export function MoonIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <path
        d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function DashboardIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 22 22" fill="none" aria-hidden {...props}>
      <rect x="3" y="3" width="7" height="9" rx="1.4" stroke="currentColor" strokeWidth={1.5} />
      <rect x="12" y="3" width="7" height="5.5" rx="1.4" stroke="currentColor" strokeWidth={1.5} />
      <rect x="12" y="10.5" width="7" height="8.5" rx="1.4" stroke="currentColor" strokeWidth={1.5} />
      <rect x="3" y="14" width="7" height="5" rx="1.4" stroke="currentColor" strokeWidth={1.5} />
    </svg>
  )
}

export function WorkflowsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 22 22" fill="none" aria-hidden {...props}>
      <circle cx="5" cy="6" r="2.3" stroke="currentColor" strokeWidth={1.5} />
      <circle cx="18" cy="6" r="2.3" stroke="currentColor" strokeWidth={1.5} />
      <circle cx="11.5" cy="17" r="2.3" stroke="currentColor" strokeWidth={1.5} />
      <path d="M7 7.3L10 14.8M16 7.3L13 14.8" stroke="currentColor" strokeWidth={1.5} />
    </svg>
  )
}

export function AgentsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 22 22" fill="none" aria-hidden {...props}>
      <rect x="3.5" y="3" width="15" height="16" rx="3" stroke="currentColor" strokeWidth={1.5} />
      <circle cx="11" cy="9.5" r="2.6" stroke="currentColor" strokeWidth={1.5} />
      <path
        d="M6.5 15.5C7.5 13.2 9 12.2 11 12.2C13 12.2 14.5 13.2 15.5 15.5"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
      />
    </svg>
  )
}

export function KnowledgeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 22 22" fill="none" aria-hidden {...props}>
      <rect x="4.5" y="2.5" width="13" height="17" rx="1.6" stroke="currentColor" strokeWidth={1.5} />
      <path
        d="M7.5 7.5H14.5M7.5 11H14.5M7.5 14.5H12"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
      />
    </svg>
  )
}

export function RunsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 22 22" fill="none" aria-hidden {...props}>
      <circle cx="11" cy="11" r="8.2" stroke="currentColor" strokeWidth={1.5} />
      <path d="M9 7.5L14.5 11L9 14.5V7.5Z" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  )
}

export function ApprovalsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 22 22" fill="none" aria-hidden {...props}>
      <rect x="3.5" y="3.5" width="15" height="15" rx="3" stroke="currentColor" strokeWidth={1.5} />
      <path
        d="M7 11.3L9.8 14.2L15.2 8.3"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
