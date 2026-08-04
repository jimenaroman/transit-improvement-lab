import type { RouteComparison, RouteScenario } from './types'

const API_BASE_URL = 'http://localhost:8000'

export async function fetchRoutes(): Promise<RouteScenario[]> {
  const res = await fetch(`${API_BASE_URL}/api/routes`)
  if (!res.ok) {
    throw new Error(`Failed to fetch routes (${res.status})`)
  }
  return res.json()
}

export async function fetchRouteComparison(routeId: number): Promise<RouteComparison> {
  const res = await fetch(`${API_BASE_URL}/api/routes/${routeId}/comparison`)
  if (!res.ok) {
    throw new Error(`Failed to fetch comparison for route ${routeId} (${res.status})`)
  }
  return res.json()
}
