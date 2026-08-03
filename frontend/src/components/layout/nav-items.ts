import type { ComponentType, SVGProps } from 'react'
import {
  AgentsIcon,
  ApprovalsIcon,
  DashboardIcon,
  KnowledgeIcon,
  RunsIcon,
  WorkflowsIcon,
} from '@/components/layout/icons'

export interface NavItem {
  to: string
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
}

/** Single source of truth for both the dock and the top-bar breadcrumb. */
export const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { to: '/workflows', label: 'Workflows', icon: WorkflowsIcon },
  { to: '/agents', label: 'Agents', icon: AgentsIcon },
  { to: '/knowledge', label: 'Knowledge', icon: KnowledgeIcon },
  { to: '/runs', label: 'Runs', icon: RunsIcon },
  { to: '/approvals', label: 'Approvals', icon: ApprovalsIcon },
]
