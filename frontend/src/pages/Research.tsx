import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchDashboardSummary } from '@/api'
import type { DashboardSummary } from '@/types'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SiteFooter } from '@/components/layout/SiteFooter'

export default function Research() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardSummary()
      .then(setDashboard)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <div className="mx-auto flex max-w-[1240px] flex-col gap-8 px-5 pt-10 pb-16 sm:gap-9 sm:px-14 sm:pt-14">
        <div className="flex flex-col gap-3.5">
          <div className="font-mono text-[11px] font-medium tracking-[.14em] text-primary uppercase">
            {loading ? 'Aggregates' : `Aggregates · ${dashboard?.total_routes ?? 0} analyzed scenarios`}
          </div>
          <h1 className="max-w-[780px] text-3xl leading-tight font-semibold tracking-tight text-balance text-foreground sm:text-4xl">
            Across every scenario analyzed so far, here's where transit time goes.
          </h1>
          <p className="max-w-[640px] text-[15px] leading-relaxed text-(--neutral-500)">
            Every scenario is a curated origin–destination pair, optionally matched to a scheduled GTFS route.
            Figures below come from the live dashboard-summary API.
          </p>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Couldn't load the dashboard</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading && (
          <div className="grid gap-3.5 sm:grid-cols-2">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {dashboard && (
          <>
            <div className="grid gap-3.5 sm:grid-cols-2">
              <div className="rounded-[9px] border border-border px-5 py-4.5">
                <div className="mb-2.5 text-[11px] text-(--neutral-600)">Total routes</div>
                <div className="font-mono text-3xl font-semibold text-(--neutral-300)">{dashboard.total_routes}</div>
              </div>
              <div className="rounded-[9px] border border-border px-5 py-4.5">
                <div className="mb-2.5 text-[11px] text-(--neutral-600)">Average transit penalty</div>
                <div className="font-mono text-3xl font-semibold text-accent">
                  {dashboard.average_transit_penalty}×
                </div>
              </div>
            </div>

            <Tabs defaultValue="overview">
              <TabsList variant="line" className="border-b border-border">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="by-city">By city</TabsTrigger>
                <TabsTrigger value="worst">Worst routes</TabsTrigger>
                <TabsTrigger value="categories">Categories</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="pt-5">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="flex flex-col gap-2">
                    <span className="text-[11px] text-(--neutral-600)">Total routes</span>
                    <span className="font-mono text-2xl font-semibold text-(--neutral-300)">
                      {dashboard.total_routes}
                    </span>
                  </div>
                  <div className="flex flex-col gap-2">
                    <span className="text-[11px] text-(--neutral-600)">Average transit penalty</span>
                    <span className="font-mono text-2xl font-semibold text-accent">
                      {dashboard.average_transit_penalty}×
                    </span>
                  </div>
                  {dashboard.average_transit_penalty_by_city.map((entry) => (
                    <div key={entry.city} className="flex flex-col gap-2">
                      <span className="text-[11px] text-(--neutral-600)">{entry.city} average</span>
                      <span className="font-mono text-2xl font-semibold text-(--neutral-300)">
                        {entry.average_transit_penalty}×
                      </span>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="by-city" className="pt-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="flex flex-col gap-4">
                    <div className="text-sm font-semibold text-(--neutral-200)">Average transit penalty by city</div>
                    <div className="flex flex-col gap-3">
                      {dashboard.average_transit_penalty_by_city.map((entry) => (
                        <div key={entry.city} className="flex items-center justify-between gap-3 border-b border-border pb-2.5">
                          <span className="text-sm text-(--neutral-400)">{entry.city}</span>
                          <span className="font-mono text-sm font-medium text-accent">
                            {entry.average_transit_penalty}×
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col gap-4">
                    <div className="text-sm font-semibold text-(--neutral-200)">
                      Average wait/transfer minutes by city
                    </div>
                    <div className="flex flex-col gap-3">
                      {dashboard.average_wait_transfer_minutes_by_city.map((entry) => (
                        <div key={entry.city} className="flex items-center justify-between gap-3 border-b border-border pb-2.5">
                          <span className="text-sm text-(--neutral-400)">{entry.city}</span>
                          <span className="font-mono text-sm font-medium text-(--neutral-300)">
                            {entry.average_wait_transfer_minutes} min
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="worst" className="pt-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  {dashboard.worst_route_by_transit_penalty && (
                    <div className="flex flex-col gap-2 rounded-[9px] border border-border p-5">
                      <div className="text-sm font-semibold text-(--neutral-200)">Worst route by transit penalty</div>
                      <Link
                        to={`/analyze-trip?routeId=${dashboard.worst_route_by_transit_penalty.id}`}
                        className="text-sm text-(--neutral-400) hover:text-foreground"
                      >
                        {dashboard.worst_route_by_transit_penalty.city}:{' '}
                        {dashboard.worst_route_by_transit_penalty.origin_label} →{' '}
                        {dashboard.worst_route_by_transit_penalty.destination_label}
                      </Link>
                      <div className="font-mono text-lg font-semibold text-accent">
                        {dashboard.worst_route_by_transit_penalty.transit_penalty}× transit penalty
                      </div>
                    </div>
                  )}
                  {dashboard.worst_route_by_wait_transfer_minutes && (
                    <div className="flex flex-col gap-2 rounded-[9px] border border-border p-5">
                      <div className="text-sm font-semibold text-(--neutral-200)">
                        Worst route by wait/transfer time
                      </div>
                      <Link
                        to={`/analyze-trip?routeId=${dashboard.worst_route_by_wait_transfer_minutes.id}`}
                        className="text-sm text-(--neutral-400) hover:text-foreground"
                      >
                        {dashboard.worst_route_by_wait_transfer_minutes.city}:{' '}
                        {dashboard.worst_route_by_wait_transfer_minutes.origin_label} →{' '}
                        {dashboard.worst_route_by_wait_transfer_minutes.destination_label}
                      </Link>
                      <div className="font-mono text-lg font-semibold text-accent">
                        {dashboard.worst_route_by_wait_transfer_minutes.wait_transfer_minutes} min wait/transfer
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="categories" className="pt-5">
                <div className="flex flex-col">
                  {dashboard.route_count_by_category.map((entry) => (
                    <div
                      key={entry.route_category}
                      className="flex items-center justify-between gap-3 border-b border-border py-3 last:border-b-0"
                    >
                      <span className="text-sm text-(--neutral-400)">{entry.route_category}</span>
                      <span className="font-mono text-sm font-medium text-(--neutral-300)">{entry.count}</span>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </Tabs>

            <Link
              to="/analyze-trip"
              className="font-mono text-[13px] font-medium text-primary hover:text-primary/80"
            >
              Open a scenario in Analyze Trip →
            </Link>
          </>
        )}
      </div>

      <SiteFooter note="Aggregates derive from scheduled GTFS service and the dashboard-summary API" maxWidthClassName="max-w-[1240px]" />
    </>
  )
}
