import * as Location from "expo-location";
import { useCallback, useState } from "react";

interface LocationState {
  status: "idle" | "requesting" | "granted" | "denied" | "unavailable";
  coords: { latitude: number; longitude: number } | null;
}

export function useLocation() {
  const [state, setState] = useState<LocationState>({ status: "idle", coords: null });

  const requestLocation = useCallback(async () => {
    setState((s) => ({ ...s, status: "requesting" }));
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        setState({ status: "denied", coords: null });
        return null;
      }
      const position = await Location.getCurrentPositionAsync({});
      const coords = { latitude: position.coords.latitude, longitude: position.coords.longitude };
      setState({ status: "granted", coords });
      return coords;
    } catch {
      setState({ status: "unavailable", coords: null });
      return null;
    }
  }, []);

  return { ...state, requestLocation };
}
