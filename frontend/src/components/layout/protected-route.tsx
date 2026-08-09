import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'

/** Redirects to /login when there's no access token — reactive, so an
 * axios interceptor clearing the store mid-session (see lib/api.ts's
 * refresh-failure path) bounces the user out on the next render too. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((state) => state.accessToken)
  if (!accessToken) {
    return <Navigate to="/login" replace />
  }
  return children
}

/** The inverse — keeps an already-signed-in user off /login and /register. */
export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((state) => state.accessToken)
  if (accessToken) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}
