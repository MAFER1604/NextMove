export type RouteCoordinate = {
  latitude: number;
  longitude: number;
};

export type RouteSegmentType = "to_pickup" | "to_dropoff" | "to_destination" | "direct" | "completed";

export type RouteSegment = {
  type: RouteSegmentType;
  coordinates: RouteCoordinate[];
  distanceKm: number;
  durationMin: number;
  trafficDelayMin: number;
};

// Forma exacta que devuelve el backend real (GET .../route, y embebida en
// cada recomendación). "provider" deja explícito si la geometría vino de
// TomTom en vivo o del respaldo precomputado — nunca se oculta.
export interface RouteData {
  provider: "tomtom" | "precomputed";
  calculatedAt: string;
  totalDistanceKm: number;
  totalDurationMin: number;
  trafficDelayMin: number;
  segments: RouteSegment[];
  version: number;
}

// Forma que usan los hooks/pantallas internamente (independiente de si el
// origen fue el backend real o el simulado).
export interface RoutePlan {
  segments: RouteSegment[];
  directSegment: RouteSegment | null;
  provider?: "tomtom" | "precomputed" | "simulated";
}
