import type { GtfsServiceContext, RouteComparison } from '@/types'

export interface TimeBurden {
  label: string
  minutes: number
  percentOfTrip: number
}

export function getMainTimeBurden(comparison: RouteComparison): TimeBurden | null {
  const { route, recommended_improvement } = comparison

  switch (recommended_improvement.category) {
    case 'frequency':
    case 'transfer_coordination':
      return {
        label: 'Wait/transfer time',
        minutes: route.wait_transfer_minutes,
        percentOfTrip: Math.round((route.wait_transfer_minutes / route.transit_minutes) * 100),
      }
    case 'stop_access':
      return {
        label: 'Walking time',
        minutes: route.walking_minutes,
        percentOfTrip: Math.round((route.walking_minutes / route.transit_minutes) * 100),
      }
    default:
      return null
  }
}

export function formatRouteName(context: GtfsServiceContext): string {
  if (context.route_short_name && context.route_long_name) {
    return `${context.route_short_name} — ${context.route_long_name}`
  }
  return context.route_long_name || context.route_short_name || context.route_id
}

export function formatMinutes(value: number | null): string {
  return value === null ? '—' : `${value} min`
}

export function formatHours(value: number | null): string {
  return value === null ? '—' : `${value} hr`
}

export function capitalize(value: string): string {
  return value.length === 0 ? value : value.charAt(0).toUpperCase() + value.slice(1)
}
