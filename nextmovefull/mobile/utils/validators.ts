import { GeoPoint } from "../types/session";

export interface ValidationResult {
  valid: boolean;
  errors: Partial<Record<"origin" | "destination" | "deadline" | "vehicle", string>>;
}

export function validateSetup(params: {
  origin: GeoPoint | null;
  destination: GeoPoint | null;
  deadline: Date | null;
  vehicle: string | null;
}): ValidationResult {
  const errors: ValidationResult["errors"] = {};

  if (!params.origin) errors.origin = "Choose your current location.";
  if (!params.destination) errors.destination = "Choose where you're heading.";
  if (!params.deadline) errors.deadline = "Set the time you need to arrive by.";
  if (!params.vehicle) errors.vehicle = "Pick a vehicle.";

  return { valid: Object.keys(errors).length === 0, errors };
}
