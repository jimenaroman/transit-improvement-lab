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
  current_transit_minutes: number
  new_transit_minutes: number
  current_transit_penalty: number
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

export interface RouteComparison {
  route: RouteScenario
  current_metrics: CurrentRouteMetrics
  recommended_improvement: RecommendedImprovement
}
