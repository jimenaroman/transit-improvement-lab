import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { fetchRouteComparison, fetchRoutes } from './api'
import type { RouteComparison, RouteScenario } from './types'

interface TimeBurden {
  label: string
  minutes: number
  percentOfTrip: number
}

function getMainTimeBurden(comparison: RouteComparison): TimeBurden | null {
  const { route, recommended_improvement } = comparison

  switch (recommended_improvement.category) {
    case 'frequency':
    case 'transfer_coordination':
      return {
        label: 'Wait/transfer time',
        minutes: route.wait_transfer_minutes,
        percentOfTrip: Math.round((route.wait_transfer_minutes / route.transit_minutes) * 100),
      }
    case 'stop_access':
      return {
        label: 'Walking time',
        minutes: route.walking_minutes,
        percentOfTrip: Math.round((route.walking_minutes / route.transit_minutes) * 100),
      }
    default:
      return null
  }
}

const ALL_CITIES = 'All'

function App() {
  const [routes, setRoutes] = useState<RouteScenario[]>([])
  const [routesError, setRoutesError] = useState<string | null>(null)

  const [cityFilter, setCityFilter] = useState(ALL_CITIES)
  const [searchText, setSearchText] = useState('')

  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null)
  const [comparison, setComparison] = useState<RouteComparison | null>(null)
  const [comparisonError, setComparisonError] = useState<string | null>(null)
  const [comparisonLoading, setComparisonLoading] = useState(false)

  useEffect(() => {
    fetchRoutes()
      .then(setRoutes)
      .catch((err: Error) => setRoutesError(err.message))
  }, [])

  const cities = useMemo(
    () => Array.from(new Set(routes.map((route) => route.city))).sort(),
    [routes],
  )

  const matchingRoutes = useMemo(() => {
    const query = searchText.trim().toLowerCase()

    return routes.filter((route) => {
      const matchesCity = cityFilter === ALL_CITIES || route.city === cityFilter
      const matchesQuery =
        query === '' ||
        route.origin_label.toLowerCase().includes(query) ||
        route.destination_label.toLowerCase().includes(query)

      return matchesCity && matchesQuery
    })
  }, [routes, cityFilter, searchText])

  const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? null

  function handleSelectRoute(routeId: number) {
    setSelectedRouteId(routeId)
    setComparison(null)
    setComparisonError(null)
  }

  function handleAnalyzeRoute() {
    if (selectedRouteId === null) {
      return
    }

    setComparison(null)
    setComparisonError(null)
    setComparisonLoading(true)

    fetchRouteComparison(selectedRouteId)
      .then(setComparison)
      .catch((err: Error) => setComparisonError(err.message))
      .finally(() => setComparisonLoading(false))
  }

  const burden = comparison ? getMainTimeBurden(comparison) : null

  return (
    <main id="app">
      <h1>Transit Improvement Lab</h1>
      <p className="subtitle">Compare driving and transit trips across Dallas and Chicago.</p>

      {routesError && <p className="error">{routesError}</p>}

      <section className="search-panel">
        <div className="search-controls">
          <label>
            City
            <select
              value={cityFilter}
              onChange={(event) => setCityFilter(event.target.value)}
            >
              <option value={ALL_CITIES}>All</option>
              {cities.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>
          </label>

          <label>
            Search
            <input
              type="text"
              placeholder="Search origin or destination…"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </label>
        </div>

        <h3>Matching scenarios</h3>
        <div className="route-grid">
          {matchingRoutes.length === 0 && <p>No matching routes.</p>}
          {matchingRoutes.map((route) => (
            <button
              key={route.id}
              type="button"
              className={`route-card ${selectedRouteId === route.id ? 'selected' : ''}`}
              onClick={() => handleSelectRoute(route.id)}
            >
              <span className="city">{route.city}</span>
              <span className="trip">
                {route.origin_label} → {route.destination_label}
              </span>
              <span className="meta">
                {route.driving_minutes} min drive · {route.transit_minutes} min transit
              </span>
            </button>
          ))}
        </div>

        {selectedRoute && (
          <div className="selected-route">
            <p>
              Selected: {selectedRoute.origin_label} → {selectedRoute.destination_label}
            </p>
            <button type="button" onClick={handleAnalyzeRoute} disabled={comparisonLoading}>
              {comparisonLoading ? 'Analyzing…' : 'Analyze route'}
            </button>
          </div>
        )}
      </section>

      {(comparisonLoading || comparisonError || comparison) && (
        <section className="comparison">
          {comparisonLoading && <p>Loading comparison…</p>}
          {comparisonError && <p className="error">{comparisonError}</p>}
          {comparison && (
            <>
              <h2>
                {comparison.route.origin_label} → {comparison.route.destination_label}
              </h2>

              <div className="comparison-block">
                <h3>Current route</h3>
                <p>Driving: {comparison.route.driving_minutes} min</p>
                <p>Transit: {comparison.route.transit_minutes} min</p>
                <p>Transit penalty: {comparison.current_metrics.transit_penalty}×</p>
              </div>

              {burden && (
                <div className="comparison-block">
                  <h3>Main time burden</h3>
                  <p>
                    {burden.label}: {burden.minutes} min
                  </p>
                  <p>This is {burden.percentOfTrip}% of the full transit trip.</p>
                </div>
              )}

              <div className="comparison-block">
                <h3>Simulated improvement</h3>
                <p>Change: {comparison.recommended_improvement.title}</p>
                <p>How: {comparison.recommended_improvement.savings_source}</p>
                <p>New transit estimate: {comparison.recommended_improvement.new_transit_minutes} min</p>
                <p>New transit penalty: {comparison.recommended_improvement.new_transit_penalty}×</p>
              </div>

              <div className="comparison-block">
                <h3>Verdict</h3>
                <p>{comparison.recommended_improvement.verdict}</p>
                <p>{comparison.recommended_improvement.explanation}</p>
              </div>
            </>
          )}
        </section>
      )}
    </main>
  )
}

export default App
