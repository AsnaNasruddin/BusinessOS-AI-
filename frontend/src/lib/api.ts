import axios from 'axios'
import { clearTokens, getAccessToken } from '@/lib/auth'

/**
 * Single axios instance for the whole app — per the plan's "LLM providers are
 * behind an interface" principle applied to HTTP too: nothing outside this file
 * should construct its own client. Points at the FastAPI backend once Phase 1 ships.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearTokens()
    }
    return Promise.reject(error)
  },
)
