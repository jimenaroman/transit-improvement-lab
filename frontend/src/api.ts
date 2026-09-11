import type {
  DashboardSummary,
  GtfsRouteGeometry,
  PlaceSuggestion,
  ResearchSummary,
  RouteComparison,
  RouteScenario,
  TripCompareRequest,
  TripCompareResponse,
} from './types'

// VITE_API_BASE_URL points at the deployed Railway backend in production;
// unset locally, it falls back to the local dev FastAPI server.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${API_BASE_URL}/api/dashboard/summary`)
  if (!res.ok) {
    throw new Error(`Failed to fetch dashboard summary (${res.status})`)
  }
  return res.json()
}

export async function fetchResearchSummary(): Promise<ResearchSummary> {
  const res = await fetch(`${API_BASE_URL}/api/dashboard/research`)
  if (!res.ok) {
    throw new Error(`Failed to fetch research summary (${res.status})`)
  }
  return res.json()
}

export async function fetchRouteGeometry(agencySource: string, routeId: string): Promise<GtfsRouteGeometry> {
  const res = await fetch(
    `${API_BASE_URL}/api/gtfs/agencies/${encodeURIComponent(agencySource)}/routes/${encodeURIComponent(routeId)}/geometry`,
  )
  if (!res.ok) {
    throw new Error(`Failed to fetch route geometry (${res.status})`)
  }
  return res.json()
}

export async function fetchPlaceAutocomplete(input: string): Promise<PlaceSuggestion[]> {
  const res = await fetch(`${API_BASE_URL}/api/places/autocomplete?input=${encodeURIComponent(input)}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch place suggestions (${res.status})`)
  }
  return res.json()
}

export async function fetchTripComparison(request: TripCompareRequest): Promise<TripCompareResponse> {
  const res = await fetch(`${API_BASE_URL}/api/trips/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Failed to compare trip (${res.status})`)
  }
  return res.json()
}
