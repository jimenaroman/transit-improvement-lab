import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchDashboardSummary, fetchRoutes } from '@/api'
import type { DashboardSummary, RouteScenario } from '@/types'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { JourneyRibbon } from '@/components/JourneyRibbon'
import { SiteFooter } from '@/components/layout/SiteFooter'

const MEASURES = [
  {
    accent: 'var(--transit-drive)',
    title: 'Driving vs transit time',
    body: 'The same origin and destination, timed both ways for a weekday departure.',
  },
  {
    accent: 'var(--transit-wait)',
    title: 'Transit penalty',
    body: 'How many extra minutes — and how many times longer — the transit trip takes.',
  },
  {
    accent: 'var(--primary)',
    title: 'Main source of burden',
    body: 'Walking, waiting, or in-vehicle time — which one actually costs the rider.',
  },
  {
    accent: 'rgba(255,255,255,.2)',
    title: 'Simulated improvement',
    body: 'What a shorter headway on the associated route would do to the total trip time.',
  },
]

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [routes, setRoutes] = useState<RouteScenario[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([fetchDashboardSummary(), fetchRoutes()])
      .then(([dashboardSummary, routeList]) => {
        setDashboard(dashboardSummary)
        setRoutes(routeList)
      })
      .catch(() => {
        // Home degrades to its static sections if the API is unreachable.
      })
      .finally(() => setLoading(false))
  }, [])

  const featuredRoute =
    dashboard?.worst_route_by_transit_penalty &&
    routes.find((route) => route.id === dashboard.worst_route_by_transit_penalty!.id)

  return (
    <>
      <section className="border-b border-border px-5 py-16 sm:px-14 sm:py-24">
        <div className="mx-auto grid max-w-[1180px] items-end gap-10 sm:grid-cols-2 sm:gap-14">
          <div className="flex flex-col gap-5">
            <div className="font-mono text-[11px] font-medium tracking-[.14em] text-primary uppercase">
              Scheduled transit vs driving
            </div>
            <h1 className="text-4xl leading-[1.1] font-semibold tracking-tight text-balance text-foreground sm:text-5xl">
              How competitive is transit with driving — and why?
            </h1>
            <p className="max-w-[560px] text-base leading-relaxed text-(--neutral-500) text-pretty">
              Transit Improvement Lab compares a curated set of real trips against the same trip by car, then uses
              scheduled GTFS service data to explain where the extra time goes and what a realistic service change
              would recover.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/analyze-trip" className={buttonVariants({ size: 'lg', className: 'h-auto px-6 py-3.5 text-sm font-semibold' })}>
                Analyze a trip
              </Link>
              <Link to="/research" className="self-center px-1 py-3.5 font-sans text-[13px] font-medium text-(--neutral-500) hover:text-foreground">
                or view the research →
              </Link>
            </div>
          </div>

          <div className="flex flex-col gap-4.5 rounded-[10px] border border-border bg-white/2 p-5.5">
            <div className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
              Featured scenario
            </div>
            {loading && (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-6 w-3/4" />
              </div>
            )}
            {!loading && featuredRoute && dashboard?.worst_route_by_transit_penalty && (
              <>
                <JourneyRibbon
                  drivingMinutes={featuredRoute.driving_minutes}
                  transitMinutes={featuredRoute.transit_minutes}
                  walkingMinutes={featuredRoute.walking_minutes}
                  waitTransferMinutes={featuredRoute.wait_transfer_minutes}
                />
                <div className="text-xl leading-tight font-semibold tracking-tight text-foreground">
                  {featuredRoute.origin_label} → {featuredRoute.destination_label} takes{' '}
                  <span className="text-accent">{dashboard.worst_route_by_transit_penalty.transit_penalty}×</span>{' '}
                  longer by transit.
                </div>
                <Link
                  to={`/analyze-trip?routeId=${featuredRoute.id}`}
                  className="font-mono text-xs font-medium text-primary hover:text-primary/80"
                >
                  Open this scenario →
                </Link>
              </>
            )}
            {!loading && !featuredRoute && (
              <p className="text-sm text-(--neutral-600)">
                Couldn't reach the API to load a featured scenario. Start the backend and refresh.
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="border-b border-border px-5 py-10 sm:px-14 sm:py-14">
        <div className="mx-auto flex max-w-[1180px] flex-col gap-5">
          <div className="font-mono text-[11px] font-medium tracking-[.14em] text-(--neutral-700) uppercase">
            Two cities, two agencies
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {dashboard?.average_transit_penalty_by_city.map((entry) => (
              <div key={entry.city} className="flex flex-col gap-3 rounded-[9px] border border-border p-5.5">
                <div className="flex items-baseline justify-between gap-3">
                  <div className="text-lg font-semibold text-(--neutral-200)">{entry.city}</div>
                  <div className="font-mono text-[11px] font-medium text-accent">
                    {entry.average_transit_penalty}× average
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-(--neutral-500)">
                  Compares {routes.filter((r) => r.city === entry.city).length} curated {entry.city} scenarios against
                  the same trip by car, using each route's linked scheduled GTFS service.
                </p>
              </div>
            ))}
            {!dashboard && (
              <>
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </>
            )}
          </div>
        </div>
      </section>

      <section className="border-b border-border px-5 py-10 sm:px-14 sm:py-14">
        <div className="mx-auto flex max-w-[1180px] flex-col gap-5.5">
          <div className="font-mono text-[11px] font-medium tracking-[.14em] text-(--neutral-700) uppercase">
            What the tool measures
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {MEASURES.map((measure) => (
              <div
                key={measure.title}
                className="flex flex-col gap-2 border-t-2 pt-4"
                style={{ borderTopColor: measure.accent }}
              >
                <div className="text-[15px] font-semibold text-(--neutral-200)">{measure.title}</div>
                <p className="text-[13px] leading-relaxed text-(--neutral-500)">{measure.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 py-10 sm:px-14 sm:py-14">
        <div className="mx-auto grid max-w-[1180px] gap-8 sm:grid-cols-2 sm:gap-11">
          <div className="flex flex-col gap-3.5">
            <div className="font-mono text-[11px] font-medium tracking-[.14em] text-(--neutral-700) uppercase">
              Data sources
            </div>
            <h2 className="text-2xl leading-tight font-semibold tracking-tight text-foreground">
              Built on published GTFS schedules, not real-time feeds
            </h2>
            <p className="max-w-[520px] text-sm leading-relaxed text-(--neutral-500)">
              Service quality comes from each agency's scheduled GTFS data: route and agency identity, average
              headway, frequency classification, and daily service span for the selected date. Nothing here tracks
              vehicles.
            </p>
            <Link to="/methodology" className="font-mono text-[13px] font-medium text-primary hover:text-primary/80">
              Read the methodology →
            </Link>
          </div>
          <div className="flex flex-col gap-2.5">
            <div className="flex justify-between gap-4 border-b border-border pb-2.5">
              <span className="text-[13px] text-(--neutral-500)">DART scheduled GTFS</span>
              <span className="font-mono text-xs font-medium text-(--neutral-300)">Dallas</span>
            </div>
            <div className="flex justify-between gap-4 border-b border-border pb-2.5">
              <span className="text-[13px] text-(--neutral-500)">CTA scheduled GTFS</span>
              <span className="font-mono text-xs font-medium text-(--neutral-300)">Chicago</span>
            </div>
            <div className="flex justify-between gap-4 border-b border-border pb-2.5">
              <span className="text-[13px] text-(--neutral-500)">Curated trip scenarios</span>
              <span className="font-mono text-xs font-medium text-(--neutral-300)">
                {dashboard ? `${dashboard.total_routes} trips` : '—'}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-[13px] text-(--neutral-500)">Real-time vehicle data</span>
              <span className="font-mono text-xs font-medium text-(--neutral-700)">not used</span>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter note="Transit Improvement Lab · scheduled-service analysis" />
    </>
  )
}
