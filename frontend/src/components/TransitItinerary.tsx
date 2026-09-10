import type { TripItineraryLeg } from '@/types'

interface TransitItineraryProps {
  legs: TripItineraryLeg[]
  totalMinutes: number
  originLabel: string
  destinationLabel: string
}

const KIND_COLOR: Record<TripItineraryLeg['kind'], string> = {
  walk: 'var(--transit-walk)',
  ride: 'var(--transit-ride)',
  wait: 'var(--transit-wait)',
}

const KIND_TEXT_ON_FILL: Record<TripItineraryLeg['kind'], string> = {
  walk: 'var(--neutral-100)',
  ride: 'var(--primary-foreground)',
  wait: '#241a05',
}

function legDisplayLabel(leg: TripItineraryLeg): string {
  if (leg.kind === 'walk') return 'Walk'
  if (leg.kind === 'wait') return 'Transfer'
  return leg.label
}

// The node BEFORE leg[i] is already known; this derives the node AFTER it --
// a ride's own name, "Transfer" before the next ride, or the trip's actual
// destination once no ride remains ahead.
function buildNodes(legs: TripItineraryLeg[], originLabel: string, destinationLabel: string): string[] {
  const nodes = [originLabel]

  legs.forEach((leg, index) => {
    if (leg.kind === 'ride') {
      const hasLaterRide = legs.slice(index + 1).some((later) => later.kind === 'ride')
      nodes.push(hasLaterRide ? 'Transfer' : destinationLabel)
      return
    }
    const nextRide = legs.slice(index + 1).find((later) => later.kind === 'ride')
    nodes.push(nextRide ? nextRide.label : destinationLabel)
  })

  return nodes
}

export function TransitItinerary({ legs, totalMinutes, originLabel, destinationLabel }: TransitItineraryProps) {
  if (legs.length === 0) return null

  const ribbonTotal = legs.reduce((sum, leg) => sum + (leg.duration_minutes ?? 0), 0) || 1
  const nodes = buildNodes(legs, originLabel, destinationLabel)

  return (
    <div className="flex flex-col gap-4 rounded-[9px] border border-border p-5 sm:p-6">
      <div className="font-mono text-sm font-semibold tracking-[.08em] text-(--neutral-200) uppercase">
        {totalMinutes} min total
      </div>

      <div className="flex h-8 gap-0.5 overflow-hidden rounded-md">
        {legs.map((leg, index) => {
          const width = ((leg.duration_minutes ?? 0) / ribbonTotal) * 100
          if (width <= 0) return null
          return (
            <div
              key={index}
              className="flex items-center justify-center overflow-hidden text-[10px] font-semibold whitespace-nowrap"
              style={{ width: `${width}%`, backgroundColor: KIND_COLOR[leg.kind], color: KIND_TEXT_ON_FILL[leg.kind] }}
              title={`${legDisplayLabel(leg)} · ${leg.duration_minutes ?? '—'} min`}
            >
              {width > 8 ? `${legDisplayLabel(leg)} ${leg.duration_minutes ?? '—'}` : ''}
            </div>
          )
        })}
      </div>

      <div className="flex flex-col">
        <div className="text-sm font-medium text-(--neutral-200)">{nodes[0]}</div>
        {legs.map((leg, index) => (
          <div key={index} className="flex flex-col">
            <div className="flex items-center gap-2 py-1 pl-1 font-mono text-xs text-(--neutral-600)">
              <span aria-hidden style={{ color: KIND_COLOR[leg.kind] }}>
                ↓
              </span>
              <span>
                {leg.kind} {leg.duration_minutes !== null ? `${leg.duration_minutes} min` : '— min'}
              </span>
            </div>
            <div className="text-sm font-medium text-(--neutral-200)">{nodes[index + 1]}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
