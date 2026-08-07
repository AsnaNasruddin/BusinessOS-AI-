import axios from 'axios'
import { useAuthStore } from '@/stores/auth-store'
import type { Membership, User } from '@/types'

/**
 * Single axios instance for the whole app — per the plan's "LLM providers are
 * behind an interface" principle applied to HTTP too: nothing outside this file
 * should construct its own client. Points at the FastAPI backend (Section 8:
 * every non-auth route expects a JWT + an org-scope header, sent here as
 * `X-Org-Id` — see the implementation plan addendum's deps.py for the
 * server-side half of this contract).
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const { accessToken, currentOrgId } = useAuthStore.getState()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  if (currentOrgId) {
    config.headers['X-Org-Id'] = currentOrgId
  }
  return config
})

/** Raw shape of `GET /auth/me` — the backend responds in snake_case; nothing
 * about that maps onto our camelCase domain types automatically. */
interface MeResponseRaw {
  user: { id: string; email: string; full_name: string }
  memberships: Array<{
    org_id: string
    org_name: string
    org_slug: string
    role: Membership['role']
  }>
}

export async function fetchProfile(): Promise<{ user: User; memberships: Membership[] }> {
  const { data } = await api.get<MeResponseRaw>('/auth/me')
  return {
    user: {
      id: data.user.id,
      email: data.user.email,
      fullName: data.user.full_name,
    },
    memberships: data.memberships.map((m) => ({
      orgId: m.org_id,
      orgName: m.org_name,
      orgSlug: m.org_slug,
      role: m.role,
    })),
  }
}

let refreshInFlight: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const { refreshToken } = useAuthStore.getState()
  if (!refreshToken) throw new Error('No refresh token available.')

  const response = await axios.post(`${api.defaults.baseURL}/auth/refresh`, {
    refresh_token: refreshToken,
  })
  const newAccessToken: string = response.data.access_token
  useAuthStore.setState({ accessToken: newAccessToken })
  return newAccessToken
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const isAuthRoute = original?.url?.includes('/auth/')

    if (error.response?.status === 401 && !original?._retry && !isAuthRoute) {
      original._retry = true
      try {
        refreshInFlight ??= refreshAccessToken().finally(() => {
          refreshInFlight = null
        })
        const newAccessToken = await refreshInFlight
        original.headers.Authorization = `Bearer ${newAccessToken}`
        return api(original)
      } catch {
        useAuthStore.getState().logout()
      }
    }

    return Promise.reject(error)
  },
)
