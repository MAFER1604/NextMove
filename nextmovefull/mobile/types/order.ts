import { GeoPoint } from "./session";

export type OfferStatus = "available" | "accepted" | "expired" | "skipped" | "taken";

export interface OrderOffer {
  id: string;
  restaurantName: string;
  dropoffLabel: string;
  netEarnings: number;
  grossPay: number;
  extraMinutes: number;
  extraKm: number;
  etaAtDestination: string; // ISO
  reasonShort: string;
  prepTimeMin: number;
  createdAt: string; // ISO, para calcular el conteo regresivo de 60s
  expiresAt: string; // ISO
  pickup: GeoPoint;
  dropoff: GeoPoint;
  status: OfferStatus;
  orderNumber: string; // identificador corto mostrado al usuario, ej. "#4821"
}

export interface CompletedDelivery {
  offerId: string;
  restaurantName: string;
  grossPay: number;
  cost: number;
  netEarnings: number;
  minutesUsed: number;
  completedAt: string; // ISO
}
