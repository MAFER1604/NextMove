export type Flexibility = "strict" | "balanced" | "flexible";
export type Vehicle = "bike" | "moto" | "car";

export type AppState =
  | "setup"
  | "searching"
  | "reviewing_offer"
  | "confirming_order"
  | "to_pickup"
  | "waiting_pickup"
  | "to_dropoff"
  | "delivery_completed"
  | "searching_next"
  | "to_destination"
  | "session_completed"
  | "error";

export interface GeoPoint {
  latitude: number;
  longitude: number;
  label: string;
}

export interface SessionConfig {
  currentLocation: GeoPoint;
  destination: GeoPoint;
  deadline: string; // ISO datetime
  flexibility: Flexibility;
  vehicle: Vehicle;
}

export interface SessionTotals {
  grossEarnings: number;
  netEarnings: number;
  ordersCompleted: number;
  distanceKm: number;
  incidentsAvoided: number;
  startedAt: string; // ISO
}
