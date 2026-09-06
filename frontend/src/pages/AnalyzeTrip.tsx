import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchRouteComparison, fetchRoutes } from '@/api'
import type { RouteComparison, RouteScenario } from '@/types'
import { capitalize, formatHours, formatMinutes, formatRouteName, getMainTimeBurden } from '@/lib/route-format'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { JourneyRibbon } from '@/components/JourneyRibbon'
import { RouteMap } from '@/components/RouteMap'
import { TripComparePanel } from '@/components/TripComparePanel'
import { SiteFooter } from '@/components/layout/SiteFooter'

const ALL_CITIES = 'All'

const FREQUENCY_BADGE_CLASS: Record<string, string> = {
  frequent: 'bg-primary text-primary-foreground',
  moderate: 'bg-(--neutral-400) text-[#241a05]',
  infrequent: 'bg-accent text-accent-foreground',
  minimal: 'bg-destructive/20 text-destructive',
}

export default function AnalyzeTrip() {
  const [searchParams] = useSearchParams()

  const [routes, setRoutes] = useState<RouteScenario[]>([])
  const [routesError, setRoutesError] = useState<string | null>(null)

  const [cityFilter, setCityFilter] = useState(ALL_CITIES)
  const [searchText, setSearchText] = useState('')

  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(() => {
    const routeIdParam = searchParams.get('routeId')
    return routeIdParam === null ? null : Number(routeIdParam)
  })
  const [comparison, setComparison] = useState<RouteComparison | null>(null)
  const [comparisonError, setComparisonError] = useState<string | null>(null)
  const [comparisonLoading, setComparisonLoading] = useState(false)

  useEffect(() => {
    fetchRoutes()
      .then(setRoutes)
      .catch((err: Error) => setRoutesError(err.message))
  }, [])

  const cities = useMemo(() => Array.from(new Set(routes.map((route) => route.city))).sort(), [routes])

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

  function handleAnalyzeRoute(routeId: number | null = selectedRouteId) {
    if (routeId === null) {
      return
    }

    setComparison(null)
    setComparisonError(null)
    setComparisonLoading(true)

    fetchRouteComparison(routeId)
      .then(setComparison)
      .catch((err: Error) => setComparisonError(err.message))
      .finally(() => setComparisonLoading(false))
  }

  useEffect(() => {
    const routeIdParam = searchParams.get('routeId')
    if (routeIdParam === null || routes.length === 0) {
      return
    }

    const routeId = Number(routeIdParam)
    if (!routes.some((route) => route.id === routeId)) {
      return
    }

    // One-time deep-link bootstrap from ?routeId= — deliberately fires the
    // same fetch as the "Analyze route" button once routes have loaded.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    handleAnalyzeRoute(routeId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routes])

  const burden = comparison ? getMainTimeBurden(comparison) : null

  return (
    <>
      <div className="mx-auto flex max-w-[1180px] flex-col gap-6 px-5 pt-7 pb-16 sm:gap-7 sm:px-14 sm:pt-9">
        <h1 className="text-3xl leading-tight font-semibold tracking-tight text-foreground">Analyze a trip</h1>

        <TripComparePanel />

        <Separator />

        <div className="flex flex-col gap-1.5">
          <h2 className="text-lg font-semibold text-(--neutral-200)">Or try a curated example</h2>
          <p className="text-sm text-(--neutral-600)">
            A fixed set of pre-analyzed Dallas and Chicago scenarios, useful as a demo while the trip comparison
            above is still new.
          </p>
        </div>

        {routesError && (
          <Alert variant="destructive">
            <AlertTitle>Couldn't load scenarios</AlertTitle>
            <AlertDescription>{routesError}</AlertDescription>
          </Alert>
        )}

        <section className="flex flex-col gap-3">
          <div className="flex flex-wrap items-stretch gap-2.5">
            <Select value={cityFilter} onValueChange={(value) => setCityFilter(value as string)}>
              <SelectTrigger className="h-auto py-2.5">
                <span className="font-mono text-[11px] text-(--neutral-700)">CITY</span>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_CITIES}>All</SelectItem>
                {cities.map((city) => (
                  <SelectItem key={city} value={city}>
                    {city}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="min-w-[260px] flex-1 overflow-hidden rounded-lg border border-border">
              <Command shouldFilter={false}>
                <CommandInput
                  placeholder="Search origin or destination…"
                  value={searchText}
                  onValueChange={setSearchText}
                />
                <div className="border-t border-border px-3 py-2 font-mono text-[10px] tracking-[.1em] text-(--neutral-700) uppercase">
                  {cityFilter === ALL_CITIES ? 'All cities' : cityFilter} · {matchingRoutes.length} of {routes.length}{' '}
                  curated scenarios
                </div>
                <CommandList>
                  <CommandEmpty>No matching routes.</CommandEmpty>
                  <CommandGroup>
                    {matchingRoutes.map((route) => (
                      <CommandItem
                        key={route.id}
                        value={String(route.id)}
                        data-checked={selectedRouteId === route.id}
                        onSelect={() => handleSelectRoute(route.id)}
                        className="flex items-center justify-between gap-3 py-2.5"
                      >
                        <div className="flex flex-col gap-1">
                          <span className="text-[13px] font-medium text-(--neutral-200)">
                            {route.origin_label} → {route.destination_label}
                          </span>
                          <span className="font-mono text-[11px] text-(--neutral-700)">
                            {route.driving_minutes} min drive · {route.transit_minutes} min transit
                          </span>
                        </div>
                        <Badge variant="secondary">{route.city}</Badge>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </div>

            <Button
              size="lg"
              className="h-auto self-center px-6 py-2.5 text-sm font-semibold"
              disabled={selectedRouteId === null || comparisonLoading}
              onClick={() => handleAnalyzeRoute()}
            >
              {comparisonLoading ? 'Analyzing…' : 'Analyze route'}
            </Button>
          </div>

          {selectedRoute && (
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-primary/40 bg-primary/8 px-3.5 py-2.5">
              <span className="font-mono text-[11px] text-primary">Selected</span>
              <span className="text-sm font-medium text-(--neutral-200)">
                {selectedRoute.origin_label} → {selectedRoute.destination_label}
              </span>
            </div>
          )}
        </section>

        {comparisonLoading && (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-9 w-2/3" />
            <div className="grid gap-3 sm:grid-cols-4">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
            <Skeleton className="h-40 w-full" />
          </div>
        )}

        {comparisonError && (
          <Alert variant="destructive">
            <AlertTitle>Couldn't load this comparison</AlertTitle>
            <AlertDescription>{comparisonError}</AlertDescription>
          </Alert>
        )}

        {comparison && (
          <div className="flex flex-col gap-6 sm:gap-7">
            <section className="flex flex-col gap-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2.5">
                <h2 className="text-2xl leading-tight font-semibold tracking-tight text-foreground">
                  {comparison.route.origin_label} → {comparison.route.destination_label}
                </h2>
                <div className="font-mono text-[11px] text-(--neutral-700)">
                  {comparison.route.route_category} · {comparison.route.time_period} · {comparison.route.distance_miles} mi
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="flex flex-col gap-2 rounded-[7px] border border-accent/40 bg-accent/7 px-4 py-3.5">
                  <span className="text-[11px] text-[#d0a95e]">Transit penalty</span>
                  <span className="font-mono text-2xl font-semibold text-accent">
                    {comparison.current_metrics.transit_penalty}×
                  </span>
                  <span className="font-mono text-[11px] text-[#b09256]">
                    +{comparison.route.transit_minutes - comparison.route.driving_minutes} min vs driving
                  </span>
                </div>

                <div className="flex flex-col gap-2 rounded-[7px] border border-border px-4 py-3.5">
                  <span className="text-[11px] text-(--neutral-600)">Main time burden</span>
                  {burden ? (
                    <>
                      <span className="text-lg leading-tight font-semibold text-(--neutral-200)">{burden.label}</span>
                      <Badge className="w-fit border border-accent/40 bg-transparent font-mono text-accent">
                        {burden.minutes} MIN · {burden.percentOfTrip}% OF TRIP
                      </Badge>
                    </>
                  ) : (
                    <span className="text-sm text-(--neutral-600)">Not applicable for this improvement type.</span>
                  )}
                </div>

                <Tooltip>
                  <TooltipTrigger className="flex flex-col gap-2 rounded-[7px] border border-border px-4 py-3.5 text-left">
                    <span className="text-[11px] text-(--neutral-600)">Car dependency score</span>
                    <span className="font-mono text-2xl font-semibold text-(--neutral-300)">
                      {comparison.current_metrics.car_dependency_score}
                    </span>
                    <span className="font-mono text-[11px] text-(--neutral-700)">0–100 · lower is better</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    A heuristic score combining transit penalty and time burden — how hard a car-free version of this
                    trip would be.
                  </TooltipContent>
                </Tooltip>

                <div className="flex flex-col gap-2 rounded-[7px] border border-border px-4 py-3.5">
                  <span className="text-[11px] text-(--neutral-600)">Weekly extra transit</span>
                  <span className="font-mono text-2xl font-semibold text-(--neutral-300)">
                    {comparison.current_metrics.weekly_extra_transit_hours}
                    <span className="ml-1 text-sm text-(--neutral-700)">hr</span>
                  </span>
                  <span className="font-mono text-[11px] text-(--neutral-700)">vs. driving this trip, 10x/week</span>
                </div>
              </div>
            </section>

            {comparison.gtfs_service_context.length === 0 ? (
              <Alert className="border-l-2 border-l-accent">
                <AlertTitle>No verified GTFS route association yet</AlertTitle>
                <AlertDescription>
                  Scheduled service and the frequency-based improvement are unavailable for this scenario. Driving and
                  transit times still compare.
                </AlertDescription>
              </Alert>
            ) : (
              comparison.gtfs_service_context.map((context) => (
                <Card
                  key={`${context.agency_source}-${context.route_id}`}
                  className="border-primary/35 bg-primary/6 gap-4"
                >
                  <CardHeader className="flex flex-col gap-3">
                    <div className="flex flex-wrap items-center justify-between gap-2.5">
                      <span className="font-mono text-[10px] font-medium tracking-[.12em] text-primary uppercase">
                        Scheduled transit service · GTFS
                      </span>
                      {context.role && (
                        <Badge variant="outline" className="font-mono uppercase">
                          {context.role.replace(/_/g, ' ')}
                        </Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="rounded-[3px] bg-primary px-2 py-1.5 font-mono text-[11px] font-semibold text-primary-foreground">
                        {context.agency_source}
                      </span>
                      <span className="text-lg font-semibold text-(--neutral-200)">{formatRouteName(context)}</span>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <Separator />
                    <div className="grid gap-4 sm:grid-cols-4">
                      <div>
                        <Tooltip>
                          <TooltipTrigger className="mb-2 inline-block border-b border-dotted border-white/22 text-[11px] text-(--neutral-600)">
                            Average headway
                          </TooltipTrigger>
                          <TooltipContent>
                            Mean gap between scheduled departures on the selected service date. Not an observed wait.
                          </TooltipContent>
                        </Tooltip>
                        <div className="font-mono text-lg font-semibold text-(--neutral-300)">
                          {formatMinutes(context.average_headway_minutes)}
                        </div>
                      </div>
                      <div>
                        <div className="mb-2 text-[11px] text-(--neutral-600)">Frequency</div>
                        <Badge
                          className={
                            FREQUENCY_BADGE_CLASS[context.frequency_classification] ??
                            FREQUENCY_BADGE_CLASS.moderate
                          }
                        >
                          {capitalize(context.frequency_classification)}
                        </Badge>
                      </div>
                      <div>
                        <div className="mb-2 text-[11px] text-(--neutral-600)">Service span</div>
                        <div className="font-mono text-lg font-semibold text-(--neutral-300)">
                          {formatHours(context.service_span_hours)}
                        </div>
                      </div>
                      <div>
                        <div className="mb-2 text-[11px] text-(--neutral-600)">Service date</div>
                        <div className="font-mono text-lg font-semibold text-(--neutral-300)">
                          {context.service_date}
                        </div>
                      </div>
                    </div>

                    <Accordion defaultValue={['explanation']} className="border-t border-border pt-1">
                      <AccordionItem value="explanation">
                        <AccordionTrigger>Service context explanation</AccordionTrigger>
                        <AccordionContent className="max-w-[720px] text-(--neutral-500)">
                          {context.explanation}
                        </AccordionContent>
                      </AccordionItem>
                      <AccordionItem value="headway">
                        <AccordionTrigger>Headway by period</AccordionTrigger>
                        <AccordionContent>
                          <div className="flex max-w-[520px] flex-col gap-2">
                            <div className="flex justify-between gap-3">
                              <span className="text-(--neutral-500)">Peak</span>
                              <span className="font-mono font-medium text-(--neutral-300)">
                                {formatMinutes(context.peak_headway_minutes)}
                              </span>
                            </div>
                            <div className="flex justify-between gap-3">
                              <span className="text-(--neutral-500)">Midday</span>
                              <span className="font-mono font-medium text-(--neutral-300)">
                                {formatMinutes(context.midday_headway_minutes)}
                              </span>
                            </div>
                            <div className="flex justify-between gap-3">
                              <span className="text-(--neutral-500)">Evening</span>
                              <span className="font-mono font-medium text-(--neutral-300)">
                                {formatMinutes(context.evening_headway_minutes)}
                              </span>
                            </div>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                      <AccordionItem value="match">
                        <AccordionTrigger>How this route was matched</AccordionTrigger>
                        <AccordionContent>
                          <div className="flex max-w-[560px] flex-col gap-2">
                            <div className="flex justify-between gap-3">
                              <span className="text-(--neutral-500)">Agency source</span>
                              <span className="font-mono font-medium text-(--neutral-300)">
                                {context.agency_source}
                              </span>
                            </div>
                            <div className="flex justify-between gap-3">
                              <span className="text-(--neutral-500)">Route id</span>
                              <span className="font-mono font-medium text-(--neutral-300)">{context.route_id}</span>
                            </div>
                            {context.role && (
                              <div className="flex justify-between gap-3">
                                <span className="text-(--neutral-500)">Role</span>
                                <span className="font-mono font-medium text-(--neutral-300)">
                                  {context.role.replace(/_/g, ' ')}
                                </span>
                              </div>
                            )}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </CardContent>
                </Card>
              ))
            )}

            {comparison.gtfs_service_context.map((context) => (
              <section
                key={`map-${context.agency_source}-${context.route_id}`}
                className="flex flex-col gap-3"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2.5">
                  <h3 className="text-sm font-semibold text-(--neutral-200)">
                    Route map · {context.agency_source} {formatRouteName(context)}
                  </h3>
                  <span className="font-mono text-[10px] text-(--neutral-700)">
                    real GTFS shape — not a straight line
                  </span>
                </div>
                <RouteMap
                  key={`${context.agency_source}-${context.route_id}`}
                  agencySource={context.agency_source}
                  routeId={context.route_id}
                />
              </section>
            ))}

            <section className="flex flex-col gap-3.5 rounded-[9px] border border-border p-5 sm:p-6">
              <h3 className="text-sm font-semibold text-(--neutral-200)">Journey breakdown</h3>
              <JourneyRibbon
                drivingMinutes={comparison.route.driving_minutes}
                transitMinutes={comparison.route.transit_minutes}
                walkingMinutes={comparison.route.walking_minutes}
                waitTransferMinutes={comparison.route.wait_transfer_minutes}
              />
            </section>

            <div className="grid gap-4 sm:grid-cols-2">
              <Card className="p-5 sm:p-6">
                <CardContent className="flex flex-col gap-3 px-0">
                  <div className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
                    Verdict
                  </div>
                  <div className="text-2xl leading-tight font-semibold tracking-tight text-foreground sm:text-[26px]">
                    {comparison.recommended_improvement.verdict}
                  </div>
                  <p className="text-sm leading-relaxed text-(--neutral-500)">
                    {comparison.recommended_improvement.explanation}
                  </p>
                </CardContent>
              </Card>

              <Card className="border-accent/35 bg-accent/7 p-5 sm:p-6">
                <CardContent className="flex flex-col gap-3 px-0">
                  <div className="font-mono text-[10px] font-medium tracking-[.12em] text-accent uppercase">
                    Simulated improvement
                  </div>
                  <div className="text-[15px] leading-relaxed font-medium text-foreground">
                    {comparison.recommended_improvement.title}
                  </div>
                  <div className="flex flex-wrap items-center gap-3.5">
                    <div>
                      <div className="mb-1.5 text-[11px] text-(--neutral-500)">Today</div>
                      <div className="font-mono text-lg font-semibold text-(--neutral-300)">
                        {comparison.route.transit_minutes} min
                      </div>
                    </div>
                    <div className="h-px min-w-[24px] flex-1 bg-white/18" />
                    <div>
                      <div className="mb-1.5 text-[11px] text-accent">Simulated</div>
                      <div className="font-mono text-lg font-semibold text-accent">
                        {comparison.recommended_improvement.new_transit_minutes} min
                      </div>
                    </div>
                    <div className="border-l border-white/14 pl-3.5">
                      <div className="mb-1.5 text-[11px] text-(--neutral-500)">Penalty</div>
                      <div className="font-mono text-lg font-semibold text-(--neutral-300)">
                        {comparison.current_metrics.transit_penalty}× → {comparison.recommended_improvement.new_transit_penalty}×
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-white/14 pt-2.5 text-[13px] leading-relaxed text-(--neutral-500)">
                    {comparison.recommended_improvement.savings_source} · {comparison.recommended_improvement.minutes_saved} min saved
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>

      <SiteFooter note="Transit and service figures come from the live API." />
    </>
  )
}
