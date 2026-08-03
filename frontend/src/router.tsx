import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/app-shell'
import { LoginPage } from '@/features/auth/login-page'
import { DashboardPage } from '@/features/dashboard/dashboard-page'
import { WorkflowBuilderPage } from '@/features/workflow-builder/workflow-builder-page'
import { AgentsPage } from '@/features/agents/agents-page'
import { KnowledgeBasePage } from '@/features/knowledge-base/knowledge-base-page'
import { RunsPage } from '@/features/runs/runs-page'
import { ApprovalsPage } from '@/features/approvals/approvals-page'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'workflows', element: <WorkflowBuilderPage /> },
      { path: 'agents', element: <AgentsPage /> },
      { path: 'knowledge', element: <KnowledgeBasePage /> },
      { path: 'runs', element: <RunsPage /> },
      { path: 'approvals', element: <ApprovalsPage /> },
    ],
  },
])
