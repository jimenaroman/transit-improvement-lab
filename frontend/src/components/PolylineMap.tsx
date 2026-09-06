import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

interface PolylineMapProps {
  positions: [number, number][]
  startLabel?: string
  endLabel?: string
  footerNote: string
}

// Presentational only -- callers own fetching/decoding. RouteMap (GTFS
// geometry) and the arbitrary-trip compare panel (decoded Google
// polylines) both render through this so the map itself stays consistent.
export function PolylineMap({ positions, startLabel = 'Route start', endLabel = 'Route end', footerNote }: PolylineMapProps) {
  const origin = positions[0]
  const destination = positions[positions.length - 1]

  // Passed as the initial `bounds` instead of a fixed center+zoom followed
  // by a fitBounds() effect -- that two-step approach starts tile requests
  // at the wrong zoom, then aborts them once the real extent is known.
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
          {startLabel}
        </div>
        <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
          <span className="h-2.5 w-2.5 rounded-full bg-primary" />
          {endLabel}
        </div>
        <div className="ml-auto font-mono text-[10px] text-(--neutral-800)">{footerNote}</div>
      </div>
    </div>
  )
}

export function MapEmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-[280px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-white/2 px-6 text-center">
      <span className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
        Map · no geometry
      </span>
      <span className="max-w-[420px] text-[13px] leading-relaxed text-(--neutral-600)">{label}</span>
    </div>
  )
}
