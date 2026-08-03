/**
 * Simulates network latency around the seed data so loading states are real
 * and visible. Delete this and point hooks at `api` once the FastAPI backend
 * (phases 1-3 of the implementation plan) exists.
 */
export function mockFetch<T>(data: T, ms = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms))
}
