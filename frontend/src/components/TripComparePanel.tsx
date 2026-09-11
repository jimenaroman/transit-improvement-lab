import { useState } from 'react'
import { fetchTripComparison } from '@/api'
import type { LocationInput, TripCompareResponse } from '@/types'
import { capitalize, formatHours, formatMinutes } from '@/lib/route-format'
import { decodePolyline } from '@/lib/decode-polyline'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { MapEmptyState, PolylineMap, type RouteSegment } from '@/components/PolylineMap'
import { PlaceAutocompleteInput } from '@/components/PlaceAutocompleteInput'
import { TransitItinerary } from '@/components/TransitItinerary'
import { TripAnalysis } from '@/components/TripAnalysis'

function formatDepartureTime(iso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/Chicago',
    timeZoneName: 'short',
  }).format(new Date(iso))
}

const EMPTY_LOCATION: LocationInput = { label: '' }

export function TripComparePanel() {
  const [origin, setOrigin] = useState<LocationInput>(EMPTY_LOCATION)
  const [destination, setDestination] = useState<LocationInput>(EMPTY_LOCATION)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TripCompareResponse | null>(null)

  function handleCompare() {
    if (!origin.label.trim() || !destination.label.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    fetchTripComparison({ origin, destination })
      .then(setResult)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }

  const usingTransitMap = Boolean(result?.transit.polyline)
  const tripPolyline = result?.transit.polyline ?? result?.driving.polyline ?? null

  // Decode each segment separately (rather than re-decoding the combined
  // polyline) so the drawn map is guaranteed consistent with the segments
  // used for walk/transit coloring below.
  const mapSegments: RouteSegment[] | undefined =
    usingTransitMap && result && result.transit.segments.length > 0
      ? result.transit.segments
          .filter((segment) => segment.polyline)
          .map((segment) => ({
            travelMode: segment.travel_mode,
            positions: decodePolyline(segment.polyline!),
          }))
      : undefined

  const mapPositions = mapSegments?.length
    ? mapSegments.flatMap((segment) => segment.positions)
    : tripPolyline
      ? decodePolyline(tripPolyline)
      : null

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2.5">
        <h2 className="text-xl leading-tight font-semibold tracking-tight text-foreground">Compare any trip</h2>
        <span className="font-mono text-[10px] tracking-[.1em] text-(--neutral-700) uppercase">
          Real driving + transit routing
        </span>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-[1fr_1fr_auto]">
        <PlaceAutocompleteInput
          placeholder="Origin (e.g. Bishop Arts, Dallas, TX)"
          value={origin}
          onChange={setOrigin}
        />
        <PlaceAutocompleteInput
          placeholder="Destination (e.g. Downtown Dallas, TX)"
          value={destination}
          onChange={setDestination}
        />
        <Button
          size="lg"
          className="h-auto px-6 py-2 text-sm font-semibold"
          disabled={loading || !origin.label.trim() || !destination.label.trim()}
          onClick={handleCompare}
        >
          {loading ? 'Comparing…' : 'Compare'}
        </Button>
      </div>

      {loading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-24 w-full" />
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn't compare this trip</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="font-mono text-[11px] text-(--neutral-700)">
            For a typical weekday departure: {formatDepartureTime(result.departure_time)}
          </div>

          <div className="rounded-[9px] border border-accent/40 bg-accent/7 px-5 py-4">
            <div className="text-lg leading-tight font-semibold text-foreground">{result.comparison.verdict}</div>
            <div className="mt-2 flex flex-wrap gap-5 font-mono text-sm">
              <span className="text-accent">{result.comparison.transit_penalty}× transit penalty</span>
              <span className="text-(--neutral-400)">
                {result.comparison.extra_minutes >= 0 ? '+' : ''}
                {result.comparison.extra_minutes} min vs driving
              </span>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-2 rounded-[7px] border border-(--transit-drive)/40 bg-(--transit-drive)/7 px-4 py-3.5">
              <span className="text-[11px] text-(--neutral-600)">Driving</span>
              <span className="font-mono text-2xl font-semibold text-(--neutral-200)">
                {result.driving.duration_minutes} min
              </span>
              {result.driving.distance_miles !== null && (
                <span className="font-mono text-[11px] text-(--neutral-700)">
                  {result.driving.distance_miles} mi
                </span>
              )}
            </div>
            <div className="flex flex-col gap-2 rounded-[7px] border border-primary/40 bg-primary/7 px-4 py-3.5">
              <span className="text-[11px] text-(--neutral-600)">Transit</span>
              <span className="font-mono text-2xl font-semibold text-primary">
                {result.transit.duration_minutes} min
              </span>
              <span className="font-mono text-[11px] text-(--neutral-700)">
                {result.transit.walking_minutes} min walking · {result.transit.transfers} transfer
                {result.transit.transfers === 1 ? '' : 's'}
              </span>
              {result.transit.route_names.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {result.transit.route_names.map((name) => (
                    <Badge key={name} variant="secondary">
                      {name}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>

          <TripAnalysis
            walkingMinutes={result.transit.walking_minutes}
            waitMinutes={result.transit.wait_minutes}
            ridingMinutes={result.transit.riding_minutes}
            bottlenecks={result.bottlenecks}
            recommendations={result.recommendations}
          />

          {result.transit.itinerary.length > 0 && (
            <TransitItinerary
              legs={result.transit.itinerary}
              totalMinutes={result.transit.duration_minutes}
              originLabel={result.origin}
              destinationLabel={result.destination}
            />
          )}

          {result.gtfs_service_context.length > 0 && (
            <details className="group rounded-[9px] border border-border">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-3.5 text-sm font-semibold text-(--neutral-200)">
                Scheduled GTFS service evidence ({result.gtfs_service_context.length})
                <span className="font-mono text-[11px] font-normal text-(--neutral-700) group-open:hidden">Show</span>
                <span className="hidden font-mono text-[11px] font-normal text-(--neutral-700) group-open:inline">Hide</span>
              </summary>
              <div className="flex flex-col gap-3 border-t border-border p-5 pt-4">
                {result.gtfs_service_context.map((context, index) =>
                  context.matched ? (
                    <Card key={`${context.agency_source}-${context.route_id}-${index}`} className="border-primary/35 bg-primary/6 gap-3 p-5">
                      <CardContent className="flex flex-col gap-3 px-0">
                        <div className="flex flex-wrap items-center gap-2.5">
                          <span className="rounded-[3px] bg-primary px-2 py-1.5 font-mono text-[11px] font-semibold text-primary-foreground">
                            {context.agency_source}
                          </span>
                          <span className="text-sm font-semibold text-(--neutral-200)">
                            {context.route_short_name} — {context.route_long_name}
                          </span>
                        </div>
                        <div className="grid gap-4 sm:grid-cols-3">
                          <div>
                            <div className="mb-1.5 text-[11px] text-(--neutral-600)">Average headway</div>
                            <div className="font-mono text-sm font-semibold text-(--neutral-300)">
                              {formatMinutes(context.average_headway_minutes)}
                            </div>
                          </div>
                          <div>
                            <div className="mb-1.5 text-[11px] text-(--neutral-600)">Frequency</div>
                            <div className="text-sm font-semibold text-(--neutral-300)">
                              {context.frequency_classification ? capitalize(context.frequency_classification) : '—'}
                            </div>
                          </div>
                          <div>
                            <div className="mb-1.5 text-[11px] text-(--neutral-600)">Service span</div>
                            <div className="font-mono text-sm font-semibold text-(--neutral-300)">
                              {formatHours(context.service_span_hours)}
                            </div>
                          </div>
                        </div>
                        {context.explanation && (
                          <p className="border-t border-border pt-3 text-[13px] leading-relaxed text-(--neutral-500)">
                            {context.explanation}
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <div
                      key={`unmatched-${index}`}
                      className="flex flex-wrap items-center justify-between gap-2.5 rounded-[7px] border border-dashed border-border px-4 py-3"
                    >
                      <span className="text-[13px] text-(--neutral-500)">
                        {context.route_short_name ?? context.route_long_name ?? 'Transit line'} — no GTFS service data
                      </span>
                      <span className="font-mono text-[11px] text-(--neutral-700)">{context.unmatched_reason}</span>
                    </div>
                  ),
                )}
              </div>
            </details>
          )}

          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-(--neutral-200)">Trip map</h3>
            {mapPositions && mapPositions.length > 0 ? (
              <PolylineMap
                positions={mapPositions}
                segments={mapSegments}
                startLabel="Origin"
                endLabel="Destination"
                originTooltip={`Origin — ${result.origin}`}
                destinationTooltip={`Destination — ${result.destination}`}
                footerNote={usingTransitMap ? 'Transit route (Google Routes)' : 'Driving route (Google Routes)'}
              />
            ) : (
              <MapEmptyState label="No route geometry was returned for this trip." />
            )}
          </div>
        </div>
      )}
    </section>
  )
}
