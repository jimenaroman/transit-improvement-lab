export interface RouteScenario {
  id: number
  city: string
  origin_label: string
  destination_label: string
  route_category: string
  time_period: string
  distance_miles: number
  driving_minutes: number
  transit_minutes: number
  walking_minutes: number
  wait_transfer_minutes: number
  transfers: number
  fare_cost: number
  gas_cost: number
  driving_emissions_kg: number
  transit_emissions_kg: number
  notes: string
}

export interface RecommendedImprovement {
  title: string
  category: string
  minutes_saved: number
  savings_source: string
  new_transit_minutes: number
  new_transit_penalty: number
  verdict: string
  explanation: string
}

export interface CurrentRouteMetrics {
  transit_penalty: number
  car_dependency_score: number
  weekly_extra_transit_hours: number
  emissions_saved_kg: number
}

export interface GtfsServiceContext {
  agency_source: string
  route_id: string
  route_short_name: string | null
  route_long_name: string | null
  role: string | null
  service_date: string
  average_headway_minutes: number | null
  peak_headway_minutes: number | null
  midday_headway_minutes: number | null
  evening_headway_minutes: number | null
  service_span_hours: number | null
  frequency_classification: string
  explanation: string
}

export interface RouteComparison {
  route: RouteScenario
  current_metrics: CurrentRouteMetrics
  recommended_improvement: RecommendedImprovement
  gtfs_service_context: GtfsServiceContext[]
}

export interface CityTransitPenalty {
  city: string
  average_transit_penalty: number
}

export interface CityWaitTransferMinutes {
  city: string
  average_wait_transfer_minutes: number
}

export interface WorstRouteByTransitPenalty {
  id: number
  city: string
  origin_label: string
  destination_label: string
  transit_penalty: number
}

export interface WorstRouteByWaitTransferMinutes {
  id: number
  city: string
  origin_label: string
  destination_label: string
  wait_transfer_minutes: number
}

export interface RouteCategoryCount {
  route_category: string
  count: number
}

export interface DashboardSummary {
  total_routes: number
  average_transit_penalty: number
  average_transit_penalty_by_city: CityTransitPenalty[]
  worst_route_by_transit_penalty: WorstRouteByTransitPenalty | null
  worst_route_by_wait_transfer_minutes: WorstRouteByWaitTransferMinutes | null
  average_wait_transfer_minutes_by_city: CityWaitTransferMinutes[]
  route_count_by_category: RouteCategoryCount[]
}
