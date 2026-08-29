import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchRouteGeometry } from '@/api'
import { Skeleton } from '@/components/ui/skeleton'

interface RouteMapProps {
  agencySource: string
  routeId: string
}

// Callers must render this with key={`${agencySource}-${routeId}`} so a
// route change remounts it instead of reusing stale fetch state.

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-[280px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-white/2 px-6 text-center">
      <span className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
        Map · no geometry
      </span>
      <span className="max-w-[420px] text-[13px] leading-relaxed text-(--neutral-600)">{label}</span>
    </div>
  )
}

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

  const origin = positions?.[0]
  const destination = positions && positions.length > 0 ? positions[positions.length - 1] : undefined

  if (positions === null && !failed) {
    return <Skeleton className="h-[280px] w-full rounded-lg" />
  }

  if (failed) {
    return <EmptyState label="Couldn't reach the API to load route geometry." />
  }

  if (!positions || positions.length === 0 || !origin || !destination) {
    return <EmptyState label="No GTFS shape is on file for this route yet, so no route line can be drawn." />
  }

  // Passed as the initial `bounds` instead of a fixed center+zoom followed
  // by a fitBounds() effect -- that two-step approach was starting tile
  // requests at the wrong zoom, then aborting them a moment later once the
  // real extent was known, which showed up as a blank flash.
  const bounds = positions.reduce<[[number, number], [number, number]]>(
    (acc, [lat, lon]) => [
      [Math.min(acc[0][0], lat), Math.min(acc[0][1], lon)],
      [Math.max(acc[1][0], lat), Math.max(acc[1][1], lon)],
    ],
    [
      [origin[0], origin[1]],
      [origin[0], origin[1]],
    ],
  )

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <MapContainer
        bounds={bounds}
        boundsOptions={{ padding: [28, 28] }}
        scrollWheelZoom={false}
        style={{ height: 280, width: '100%', background: '#0b1410' }}
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, OpenStreetMap contributors, and the GIS community"
        />
        <Polyline positions={positions} pathOptions={{ color: '#22b45c', weight: 3.5, opacity: 0.9 }} />
        <CircleMarker
          center={origin}
          radius={6}
          pathOptions={{ color: '#e8c247', fillColor: '#e8c247', fillOpacity: 1, weight: 2 }}
        />
        <CircleMarker
          center={destination}
          radius={6}
          pathOptions={{ color: '#22b45c', fillColor: '#22b45c', fillOpacity: 1, weight: 2 }}
        />
      </MapContainer>
      <div className="flex flex-wrap items-center gap-4 border-t border-border px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
          <span className="h-2.5 w-2.5 rounded-full bg-accent" />
          Route start
        </div>
        <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
          <span className="h-2.5 w-2.5 rounded-full bg-primary" />
          Route end
        </div>
        <div className="ml-auto font-mono text-[10px] text-(--neutral-800)">
          GTFS shape · {positions.length} points
        </div>
      </div>
    </div>
  )
}
