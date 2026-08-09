import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Membership, User } from '@/types'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  memberships: Membership[]
  currentOrgId: string | null

  /** Sets tokens only — used right after login/register, before `/me` has
   * resolved, since the request interceptor needs an access token in place
   * to authenticate that very `/me` call. */
  setTokens: (accessToken: string, refreshToken: string) => void
  /** Sets user + memberships once `/me` resolves, defaulting the active org
   * to the first membership if none is already selected. */
  setProfile: (user: User, memberships: Membership[]) => void
  setCurrentOrg: (orgId: string) => void
  logout: () => void
}

/**
 * BusinessOS's session state — tokens, current user, and which org is
 * "active" for org-scoped requests (sent as the `X-Org-Id` header, see
 * lib/api.ts). Persisted so a page refresh doesn't force a re-login,
 * following the same persist-to-localStorage pattern as theme-store.ts.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      memberships: [],
      currentOrgId: null,

      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),

      setProfile: (user, memberships) =>
        set({
          user,
          memberships,
          currentOrgId: get().currentOrgId ?? memberships[0]?.orgId ?? null,
        }),

      setCurrentOrg: (orgId) => set({ currentOrgId: orgId }),

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          memberships: [],
          currentOrgId: null,
        }),
    }),
    {
      name: 'businessos-auth',
      // v1: pre-v1 sessions may hold a raw snake_case /auth/me response
      // (a mapping bug, since fixed) instead of the typed User/Membership
      // shape — migrating forces a clean re-login instead of rehydrating
      // corrupted data (e.g. `user.fullName === undefined`).
      version: 1,
      migrate: (_persistedState, version) =>
        version < 1
          ? { accessToken: null, refreshToken: null, user: null, memberships: [], currentOrgId: null }
          : (_persistedState as AuthState),
    },
  ),
)
