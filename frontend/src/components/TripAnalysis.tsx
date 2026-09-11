import type { TripBottleneck, TripImprovementSuggestion } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

interface TripAnalysisProps {
  walkingMinutes: number
  waitMinutes: number | null
  ridingMinutes: number
  bottlenecks: TripBottleneck[]
  recommendations: TripImprovementSuggestion[]
}

const CONFIDENCE_COLOR: Record<string, string> = {
  high: 'var(--primary)',
  moderate: 'var(--accent)',
  low: 'var(--neutral-600)',
}

// Kept separate from TransitItinerary's per-leg ribbon: this is the
// trip-level answer to "where does the extra time come from," aggregated
// by kind rather than broken out by individual ride/transfer.
function TimeBreakdownBar({
  walkingMinutes,
  waitMinutes,
  ridingMinutes,
}: {
  walkingMinutes: number
  waitMinutes: number | null
  ridingMinutes: number
}) {
  const known = waitMinutes ?? 0
  const total = walkingMinutes + known + ridingMinutes || 1
  const segments = [
    { label: 'Walk', minutes: walkingMinutes, color: 'var(--transit-walk)' },
    ...(waitMinutes === null
      ? []
      : [{ label: 'Wait/transfer', minutes: waitMinutes, color: 'var(--transit-wait)' }]),
    { label: 'Ride', minutes: ridingMinutes, color: 'var(--transit-ride)' },
  ]

  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-7 gap-0.5 overflow-hidden rounded-md">
        {segments.map((segment) => {
          const width = (segment.minutes / total) * 100
          if (width <= 0) return null
          return (
            <div
              key={segment.label}
              className="flex items-center justify-center overflow-hidden text-[10px] font-semibold whitespace-nowrap text-(--neutral-100)"
              style={{ width: `${width}%`, backgroundColor: segment.color }}
              title={`${segment.label}: ${segment.minutes} min`}
            >
              {width > 12 ? `${segment.label} ${segment.minutes}` : ''}
            </div>
          )
        })}
      </div>
      {waitMinutes === null && (
        <p className="text-[11px] text-(--neutral-700)">
          Wait/transfer time isn't shown separately -- Google didn't return real stop timestamps for this trip, so
          it isn't split out rather than guessed.
        </p>
      )}
    </div>
  )
}

function BottleneckList({ bottlenecks }: { bottlenecks: TripBottleneck[] }) {
  return (
    <div className="flex flex-col gap-2.5">
      {bottlenecks.map((bottleneck) => (
        <div key={bottleneck.category} className="flex flex-col gap-1 rounded-[7px] border border-border px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="inline-block size-2 shrink-0 rounded-full"
              style={{ backgroundColor: CONFIDENCE_COLOR[bottleneck.confidence] ?? 'var(--neutral-600)' }}
            />
            <span className="text-sm font-semibold text-(--neutral-200)">{bottleneck.label}</span>
            <Badge variant="secondary" className="font-mono text-[10px] uppercase">
              {bottleneck.confidence} confidence
            </Badge>
          </div>
          <p className="text-[13px] leading-relaxed text-(--neutral-500)">{bottleneck.evidence}</p>
        </div>
      ))}
    </div>
  )
}

function RecommendationList({ recommendations }: { recommendations: TripImprovementSuggestion[] }) {
  if (recommendations.length === 0) {
    return (
      <p className="text-[13px] text-(--neutral-600)">
        No targeted improvement is suggested -- this trip doesn't show a dominant measured bottleneck.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {recommendations.map((suggestion) => (
        <Card key={suggestion.category} className="gap-2 p-4.5">
          <CardContent className="flex flex-col gap-2 px-0">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-sm font-semibold text-(--neutral-200)">{suggestion.title}</span>
              {suggestion.estimated_impact && (
                <span className="font-mono text-[11px] text-accent">{suggestion.estimated_impact}</span>
              )}
            </div>
            <p className="text-[13px] leading-relaxed text-(--neutral-500)">{suggestion.rationale}</p>
            <p className="text-[12px] text-(--neutral-700)">Evidence: {suggestion.evidence}</p>
            <p className="text-[11px] text-(--neutral-800)">{suggestion.limitation}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function TripAnalysis({ walkingMinutes, waitMinutes, ridingMinutes, bottlenecks, recommendations }: TripAnalysisProps) {
  return (
    <div className="flex flex-col gap-5 rounded-[9px] border border-border p-5 sm:p-6">
      <div>
        <h3 className="text-sm font-semibold text-(--neutral-200)">Where the extra time goes</h3>
        <p className="text-[12px] text-(--neutral-600)">Walking, waiting/transferring, and riding, as a share of the trip.</p>
      </div>
      <TimeBreakdownBar walkingMinutes={walkingMinutes} waitMinutes={waitMinutes} ridingMinutes={ridingMinutes} />

      <div className="flex flex-col gap-2.5">
        <h3 className="text-sm font-semibold text-(--neutral-200)">What appears to be the main bottleneck</h3>
        <BottleneckList bottlenecks={bottlenecks} />
      </div>

      <div className="flex flex-col gap-2.5">
        <h3 className="text-sm font-semibold text-(--neutral-200)">What could plausibly improve it</h3>
        <RecommendationList recommendations={recommendations} />
      </div>
    </div>
  )
}
