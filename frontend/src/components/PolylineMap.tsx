import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useTheme } from '@/lib/theme'

const DARK_TILE_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
const LIGHT_TILE_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
const TILE_ATTRIBUTION = 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, OpenStreetMap contributors, and the GIS community'

export interface RouteSegment {
  travelMode: string
  positions: [number, number][]
}

interface PolylineMapProps {
  positions: [number, number][]
  segments?: RouteSegment[]
  startLabel?: string
  endLabel?: string
  originTooltip?: string
  destinationTooltip?: string
  footerNote: string
}

function segmentColor(travelMode: string): string {
  if (travelMode === 'WALK') return 'var(--transit-walk)'
  if (travelMode === 'TRANSIT') return 'var(--transit-ride)'
  return 'var(--primary)'
}

// Presentational only -- callers own fetching/decoding. RouteMap (GTFS
// geometry) and the arbitrary-trip compare panel (decoded Google
// polylines) both render through this so the map itself stays consistent.
export function PolylineMap({
  positions,
  segments,
  startLabel = 'Route start',
  endLabel = 'Route end',
  originTooltip,
  destinationTooltip,
  footerNote,
}: PolylineMapProps) {
  const { theme } = useTheme()
  const origin = positions[0]
  const destination = positions[positions.length - 1]
  const hasWalkSegment = segments?.some((segment) => segment.travelMode === 'WALK')
  const hasTransitSegment = segments?.some((segment) => segment.travelMode === 'TRANSIT')

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
        boundsOptions={{ padding: [24, 24] }}
        scrollWheelZoom={false}
        style={{ height: 280, width: '100%', background: 'var(--card)' }}
        className="[&_.leaflet-control-attribution]:bg-(--card)/85! [&_.leaflet-control-attribution]:text-(--neutral-700)!"
      >
        <TileLayer key={theme} url={theme === 'dark' ? DARK_TILE_URL : LIGHT_TILE_URL} attribution={TILE_ATTRIBUTION} />
        {segments && segments.length > 0 ? (
          segments.map((segment, index) =>
            segment.positions.length > 1 ? (
              <Polyline
                key={index}
                positions={segment.positions}
                pathOptions={{ color: segmentColor(segment.travelMode), weight: 5, opacity: 0.92 }}
              />
            ) : null,
          )
        ) : (
          <Polyline positions={positions} pathOptions={{ color: 'var(--primary)', weight: 5, opacity: 0.92 }} />
        )}
        <CircleMarker
          center={origin}
          radius={7}
          pathOptions={{ color: 'var(--card)', fillColor: 'var(--accent)', fillOpacity: 1, weight: 3 }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            {originTooltip ?? startLabel}
          </Tooltip>
        </CircleMarker>
        <CircleMarker
          center={destination}
          radius={9}
          pathOptions={{ color: 'var(--card)', fillColor: 'var(--primary)', fillOpacity: 1, weight: 3 }}
        >
          <Tooltip direction="top" offset={[0, -8]}>
            {destinationTooltip ?? endLabel}
          </Tooltip>
        </CircleMarker>
      </MapContainer>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-border px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
          <span className="h-2.5 w-2.5 rounded-full bg-accent" />
          {startLabel}
        </div>
        <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
          <span className="h-2.5 w-2.5 rounded-full bg-primary" />
          {endLabel}
        </div>
        {hasWalkSegment && (
          <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
            <span className="h-1.5 w-4 rounded-full bg-(--transit-walk)" />
            Walking
          </div>
        )}
        {hasTransitSegment && (
          <div className="flex items-center gap-2 text-xs text-(--neutral-400)">
            <span className="h-1.5 w-4 rounded-full bg-(--transit-ride)" />
            Transit
          </div>
        )}
        <div className="ml-auto font-mono text-[10px] text-(--neutral-800)">{footerNote}</div>
      </div>
    </div>
  )
}

export function MapEmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-[280px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-(--muted) px-6 text-center">
      <span className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
        Map · no geometry
      </span>
      <span className="max-w-[420px] text-[13px] leading-relaxed text-(--neutral-600)">{label}</span>
    </div>
  )
}
