import { RouteCoordinate, RouteSegment, RouteSegmentType } from "../types/route";
import { GeoPoint } from "../types/session";

export function haversineKm(a: RouteCoordinate, b: RouteCoordinate): number {
  const R = 6371;
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

// Hash determinista simple a partir de dos puntos, para que la misma pareja
// origen/destino produzca siempre la misma curva (nunca aleatoria por render).
function seededOffset(a: RouteCoordinate, b: RouteCoordinate, index: number): number {
  const raw = Math.sin((a.latitude + b.longitude) * 12.9898 + index * 78.233) * 43758.5453;
  return raw - Math.floor(raw) - 0.5; // rango [-0.5, 0.5)
}

/**
 * Genera una polyline determinista con un par de curvas suaves entre dos
 * puntos reales, para que la ruta se vea como una calle y no una línea recta
 * perfecta. Basada en coordenadas ya conocidas (nunca coordenadas al azar).
 */
export function buildDeterministicPath(from: RouteCoordinate, to: RouteCoordinate, bends = 3): RouteCoordinate[] {
  const points: RouteCoordinate[] = [from];
  const distKm = haversineKm(from, to);
  const bendMagnitude = Math.min(distKm * 0.06, 0.9) / 111; // grados aprox

  for (let i = 1; i <= bends; i++) {
    const t = i / (bends + 1);
    const baseLat = from.latitude + (to.latitude - from.latitude) * t;
    const baseLng = from.longitude + (to.longitude - from.longitude) * t;
    const perpLat = -(to.longitude - from.longitude);
    const perpLng = to.latitude - from.latitude;
    const norm = Math.sqrt(perpLat ** 2 + perpLng ** 2) || 1;
    const offset = seededOffset(from, to, i) * bendMagnitude;
    points.push({
      latitude: baseLat + (perpLat / norm) * offset,
      longitude: baseLng + (perpLng / norm) * offset,
    });
  }
  points.push(to);
  return points;
}

export function pathDistanceKm(path: RouteCoordinate[]): number {
  let total = 0;
  for (let i = 0; i < path.length - 1; i++) total += haversineKm(path[i], path[i + 1]);
  return total;
}

export function makeSegment(
  type: RouteSegmentType,
  from: GeoPoint,
  to: GeoPoint,
  speedKmh: number
): RouteSegment {
  const coordinates = buildDeterministicPath(from, to);
  const distanceKm = pathDistanceKm(coordinates);
  const durationMin = (distanceKm / speedKmh) * 60;
  return { type, coordinates, distanceKm, durationMin, trafficDelayMin: 0 };
}

/** Interpola un punto a lo largo de una polyline según una fracción 0..1. */
export function interpolateAlongPath(path: RouteCoordinate[], fraction: number): RouteCoordinate {
  if (path.length === 0) return { latitude: 0, longitude: 0 };
  if (path.length === 1 || fraction <= 0) return path[0];
  if (fraction >= 1) return path[path.length - 1];

  const idxFloat = fraction * (path.length - 1);
  const idx = Math.floor(idxFloat);
  const t = idxFloat - idx;
  const a = path[idx];
  const b = path[Math.min(idx + 1, path.length - 1)];
  return {
    latitude: a.latitude + (b.latitude - a.latitude) * t,
    longitude: a.longitude + (b.longitude - a.longitude) * t,
  };
}

export function allCoordinates(segments: RouteSegment[]): RouteCoordinate[] {
  return segments.flatMap((s) => s.coordinates);
}
