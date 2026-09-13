export const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";
export const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK !== "false"; // por defecto true

export const OFFER_COUNTDOWN_SECONDS = 60;
export const REQUEST_TIMEOUT_MS = 8000;

export const VEHICLE_PROFILES = {
  bike: { label: "Bike", speedKmh: 14, capKg: 5, capL: 15, costPerKm: 0 },
  moto: { label: "Moto", speedKmh: 32, capKg: 15, capL: 40, costPerKm: 1.2 },
  car: { label: "Car", speedKmh: 28, capKg: 40, capL: 120, costPerKm: 2.0 },
} as const;

export const FLEXIBILITY_COPY = {
  strict: "Arrive at least 10 minutes early",
  balanced: "Arrive by your selected time",
  flexible: "Allow up to 10 extra minutes",
} as const;
