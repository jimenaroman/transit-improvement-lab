import { useEffect, useState } from 'react'
import { fetchResearchSummary } from '@/api'
import type { ResearchSummary } from '@/types'
import { capitalize } from '@/lib/route-format'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { SiteFooter } from '@/components/layout/SiteFooter'
import { ScatterChart, type ScatterPoint } from '@/components/research/ScatterChart'
import { HorizontalBarList, type HorizontalBarItem } from '@/components/research/HorizontalBarList'
import { colorForGroup } from '@/components/research/chart-colors'

const formatPenalty = (value: number) => `${value.toFixed(2)}×`
const formatMinutes = (value: number) => `${Math.round(value)} min`
const formatCount = (value: number) => `${value}`

function correlationStrength(r: number): string {
  const magnitude = Math.abs(r)
  if (magnitude >= 0.6) return 'strong'
  if (magnitude >= 0.3) return 'moderate'
  return 'weak'
}

function CorrelationRow({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-b-0">
      <span className="text-[13px] text-(--neutral-400)">{label}</span>
      <span className="font-mono text-sm font-medium text-(--neutral-200)">
        {value === null ? 'not enough variance' : `r = ${value.toFixed(2)} (${correlationStrength(value)})`}
      </span>
    </div>
  )
}

export default function Research() {
  const [research, setResearch] = useState<ResearchSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchResearchSummary()
      .then(setResearch)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const cityNames = research?.average_transit_penalty_by_city.map((entry) => entry.city) ?? []

  const walkingPoints: ScatterPoint[] =
    research?.scenarios.map((s) => ({
      id: s.id,
      group: s.city,
      label: `${s.origin_label} → ${s.destination_label}`,
      x: s.walking_minutes,
      y: s.transit_penalty,
    })) ?? []

  const waitPoints: ScatterPoint[] =
    research?.scenarios.map((s) => ({
      id: s.id,
      group: s.city,
      label: `${s.origin_label} → ${s.destination_label}`,
      x: s.wait_transfer_minutes,
      y: s.transit_penalty,
    })) ?? []

  const cityBarItems: HorizontalBarItem[] =
    research?.average_transit_penalty_by_city.map((entry) => ({
      key: entry.city,
      label: entry.city,
      value: entry.average_transit_penalty,
      color: colorForGroup(entry.city, cityNames),
    })) ?? []

  const rankedItems: HorizontalBarItem[] =
    research?.scenarios
      .slice()
      .sort((a, b) => b.transit_penalty - a.transit_penalty)
      .map((s) => ({
        key: String(s.id),
        label: `${s.origin_label} → ${s.destination_label}`,
        sublabel: s.city,
        value: s.transit_penalty,
        color: colorForGroup(s.city, cityNames),
        href: `/analyze-trip?routeId=${s.id}`,
      })) ?? []

  const categoryItems: HorizontalBarItem[] =
    research?.average_transit_penalty_by_category.map((entry) => ({
      key: entry.route_category,
      label: capitalize(entry.route_category.replaceAll('_', ' ')),
      value: entry.average_transit_penalty,
      color: 'var(--accent)',
    })) ?? []

  return (
    <>
      <div className="mx-auto flex max-w-[1240px] flex-col gap-9 px-5 pt-10 pb-16 sm:px-14 sm:pt-14">
        <div className="flex flex-col gap-3.5">
          <div className="font-mono text-[11px] font-medium tracking-[.14em] text-primary uppercase">
            Exploratory analysis
          </div>
          <h1 className="max-w-[780px] text-3xl leading-tight font-semibold tracking-tight text-balance text-foreground sm:text-4xl">
            What makes a transit trip slower than driving, in this curated sample?
          </h1>
          <p className="max-w-[640px] text-[15px] leading-relaxed text-(--neutral-500)">
            Explores relationships between walking, waiting, transfers, and the transit penalty across the
            project's curated origin–destination scenarios.
          </p>
        </div>

        <Alert>
          <AlertTitle>Exploratory analysis of 12 curated origin-destination scenarios</AlertTitle>
          <AlertDescription>
            Not a representative citywide sample. Patterns below describe this sample only and should not be
            generalized to Dallas or Chicago as a whole.
          </AlertDescription>
        </Alert>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Couldn't load the research data</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading && (
          <div className="grid gap-3.5 sm:grid-cols-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {research && research.scenario_count === 0 && (
          <Alert>
            <AlertTitle>No curated scenarios yet</AlertTitle>
            <AlertDescription>Research charts will appear once scenarios exist.</AlertDescription>
          </Alert>
        )}

        {research && research.scenario_count > 0 && (
          <>
            <div className="grid gap-3.5 sm:grid-cols-4">
              <div className="rounded-[9px] border border-border px-5 py-4.5">
                <div className="mb-2.5 text-[11px] text-(--neutral-600)">Scenarios</div>
                <div className="font-mono text-2xl font-semibold text-(--neutral-300)">
                  {formatCount(research.scenario_count)}
                </div>
              </div>
              <div className="rounded-[9px] border border-border px-5 py-4.5">
                <div className="mb-2.5 text-[11px] text-(--neutral-600)">Sample average penalty</div>
                <div className="font-mono text-2xl font-semibold text-accent">
                  {formatPenalty(research.overall_average_transit_penalty)}
                </div>
              </div>
              {research.average_transit_penalty_by_city.map((entry) => (
                <div key={entry.city} className="rounded-[9px] border border-border px-5 py-4.5">
                  <div className="mb-2.5 text-[11px] text-(--neutral-600)">{entry.city} average</div>
                  <div className="font-mono text-2xl font-semibold text-(--neutral-300)">
                    {formatPenalty(entry.average_transit_penalty)}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold text-(--neutral-200)">Legend</h2>
              <div className="flex flex-wrap gap-4 font-mono text-[11px] text-(--neutral-600)">
                {cityNames.map((city) => (
                  <span key={city} className="flex items-center gap-1.5">
                    <span
                      className="inline-block size-2.5 rounded-full"
                      style={{ backgroundColor: colorForGroup(city, cityNames) }}
                    />
                    {city}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid gap-8 sm:grid-cols-2">
              <div className="flex flex-col gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-(--neutral-200)">Walking burden vs transit penalty</h2>
                  <p className="text-[12px] text-(--neutral-600)">
                    Each point is one scenario. Click a point to open it in Analyze Trip.
                  </p>
                </div>
                <ScatterChart
                  points={walkingPoints}
                  xAxisLabel="Walking minutes"
                  yAxisLabel="Transit penalty"
                  formatX={formatMinutes}
                  formatY={formatPenalty}
                />
              </div>
              <div className="flex flex-col gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-(--neutral-200)">Wait/transfer burden vs transit penalty</h2>
                  <p className="text-[12px] text-(--neutral-600)">
                    Each point is one scenario. Click a point to open it in Analyze Trip.
                  </p>
                </div>
                <ScatterChart
                  points={waitPoints}
                  xAxisLabel="Wait/transfer minutes"
                  yAxisLabel="Transit penalty"
                  formatX={formatMinutes}
                  formatY={formatPenalty}
                />
              </div>
            </div>

            <div className="grid gap-8 sm:grid-cols-2">
              <div className="flex flex-col gap-3">
                <h2 className="text-sm font-semibold text-(--neutral-200)">Average transit penalty by city</h2>
                <HorizontalBarList items={cityBarItems} formatValue={formatPenalty} />
              </div>
              <div className="flex flex-col gap-3">
                <h2 className="text-sm font-semibold text-(--neutral-200)">Average transit penalty by category</h2>
                <HorizontalBarList items={categoryItems} formatValue={formatPenalty} />
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <h2 className="text-sm font-semibold text-(--neutral-200)">Scenarios ranked by transit penalty</h2>
                <p className="text-[12px] text-(--neutral-600)">Worst first. Click a scenario to open it in Analyze Trip.</p>
              </div>
              <HorizontalBarList items={rankedItems} formatValue={formatPenalty} showRank />
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <h2 className="text-sm font-semibold text-(--neutral-200)">Exploratory correlations</h2>
                <p className="text-[12px] text-(--neutral-600)">
                  Pearson correlation across this 12-scenario sample only. Describes association, not causation.
                </p>
              </div>
              <div className="rounded-[9px] border border-border px-5">
                <CorrelationRow
                  label="Walking minutes vs transit penalty"
                  value={research.correlations.walking_minutes_vs_transit_penalty}
                />
                <CorrelationRow
                  label="Wait/transfer minutes vs transit penalty"
                  value={research.correlations.wait_transfer_minutes_vs_transit_penalty}
                />
                <CorrelationRow
                  label="Transfers vs transit penalty"
                  value={research.correlations.transfers_vs_transit_penalty}
                />
              </div>
            </div>
          </>
        )}
      </div>

      <SiteFooter
        note="Exploratory analysis of 12 curated origin-destination scenarios; not a representative citywide sample."
        maxWidthClassName="max-w-[1240px]"
      />
    </>
  )
}
