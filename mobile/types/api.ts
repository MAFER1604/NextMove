import { OrderOffer, CompletedDelivery } from "./order";
import { RoutePlan } from "./route";
import { SessionConfig, SessionTotals } from "./session";

export type AppEventType =
  | "arrival_risk"
  | "road_closure"
  | "break_needed"
  | "heat_limit"
  | "capacity_blocked"
  | "restricted_zone"
  | "restaurant_delay";

export interface AppEvent {
  type: AppEventType;
  message: string;
  detail?: string;
  severity: "info" | "warning" | "danger";
  createdAt: string; // ISO
}

export interface TickResult {
  simTimeIso: string;
  events: AppEvent[];
  arrivedAtPickup: boolean;
  arrivedAtDropoff: boolean;
  arrivedAtDestination: boolean;
}

export interface AcceptResult {
  success: boolean;
  stillAvailable: boolean;
  route: RoutePlan | null;
}

export interface DataProvider {
  isMock: boolean;
  checkConnection(): Promise<boolean>;
  startSession(config: SessionConfig): Promise<{ sessionId: string }>;
  endSession(sessionId: string): Promise<void>;
  searchOrders(sessionId: string): Promise<OrderOffer[]>;
  refreshOffer(sessionId: string, offerId: string): Promise<OrderOffer | null>;
  acceptOffer(sessionId: string, offerId: string): Promise<AcceptResult>;
  skipOffer(sessionId: string, offerId: string): Promise<void>;
  confirmPickup(sessionId: string, offerId: string): Promise<{ route: RoutePlan }>;
  confirmDropoff(sessionId: string, offerId: string): Promise<{ completed: CompletedDelivery; totals: SessionTotals }>;
  getDirectRoute(sessionId: string): Promise<RoutePlan>;
  hasTimeForMore(sessionId: string): Promise<boolean>;
  tick(sessionId: string, deltaSeconds: number): Promise<TickResult>;
  getTotals(sessionId: string): Promise<SessionTotals>;
}
