import { useEffect, useState } from 'react'
import { fetchRouteGeometry } from '@/api'
import { Skeleton } from '@/components/ui/skeleton'
import { MapEmptyState, PolylineMap } from '@/components/PolylineMap'

interface RouteMapProps {
  agencySource: string
  routeId: string
}

// Callers must render this with key={`${agencySource}-${routeId}`} so a
// route change remounts it instead of reusing stale fetch state.
export function RouteMap({ agencySource, routeId }: RouteMapProps) {
  const [positions, setPositions] = useState<[number, number][] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    fetchRouteGeometry(agencySource, routeId)
      .then((geometry) => {
        if (cancelled) return
        setPositions(geometry.points.map((point): [number, number] => [point.lat, point.lon]))
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
    }
  }, [agencySource, routeId])

  if (positions === null && !failed) {
    return <Skeleton className="h-[280px] w-full rounded-lg" />
  }

  if (failed) {
    return <MapEmptyState label="Couldn't reach the API to load route geometry." />
  }

  if (!positions || positions.length === 0) {
    return <MapEmptyState label="No GTFS shape is on file for this route yet, so no route line can be drawn." />
  }

  return <PolylineMap positions={positions} footerNote={`GTFS shape · ${positions.length} points`} />
}
