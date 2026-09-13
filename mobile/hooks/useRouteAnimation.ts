import { useEffect, useMemo, useRef, useState } from "react";
import { RouteSegment } from "../types/route";
import { RouteCoordinate } from "../types/route";
import { allCoordinates, interpolateAlongPath } from "../utils/routeHelpers";

/**
 * Calcula la posición interpolada del repartidor sobre los segmentos de ruta
 * activos, según los minutos transcurridos. Se apoya en actualizaciones
 * frecuentes y pequeñas (cada tick) en vez de saltos grandes, así que el
 * movimiento se percibe continuo sin depender de AnimatedRegion nativo.
 */
export function useRouteAnimation(segments: RouteSegment[], elapsedMin: number) {
  const path = useMemo(() => allCoordinates(segments), [segments]);
  const totalMin = useMemo(() => segments.reduce((s, seg) => s + seg.durationMin, 0) || 1, [segments]);
  const [position, setPosition] = useState<RouteCoordinate | null>(path[0] ?? null);

  useEffect(() => {
    if (path.length === 0) {
      setPosition(null);
      return;
    }
    const fraction = Math.min(Math.max(elapsedMin / totalMin, 0), 1);
    setPosition(interpolateAlongPath(path, fraction));
  }, [path, totalMin, elapsedMin]);

  return position;
}
