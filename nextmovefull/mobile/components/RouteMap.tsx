import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useRef } from "react";
import { StyleSheet, View } from "react-native";
import MapView, { Marker, Polyline, Region } from "react-native-maps";
import { colors } from "../constants/theme";
import { RouteSegment } from "../types/route";
import { GeoPoint } from "../types/session";

interface Props {
  currentLocation: GeoPoint;
  destination: GeoPoint;
  pickup?: GeoPoint | null;
  dropoff?: GeoPoint | null;
  segments: RouteSegment[];
  directSegment?: RouteSegment | null;
  incidentPoint?: GeoPoint | null;
  vehiclePosition?: { latitude: number; longitude: number } | null;
  vehicleIcon?: "bicycle" | "bicycle-outline" | "car" | "car-sport";
  fitKey?: string; // cambia cuando debe re-ajustarse el encuadre
  children?: React.ReactNode;
}

const SEGMENT_COLOR: Record<string, string> = {
  to_pickup: colors.routeToPickup,
  to_dropoff: colors.routeToDropoff,
  to_destination: colors.routeToDestination,
  direct: colors.routeDirect,
  completed: colors.routeCompleted,
};

export function RouteMap({
  currentLocation, destination, pickup, dropoff, segments, directSegment,
  incidentPoint, vehiclePosition, vehicleIcon = "car", fitKey,
}: Props) {
  const mapRef = useRef<MapView>(null);

  useEffect(() => {
    const allPoints = [
      currentLocation,
      destination,
      ...(pickup ? [pickup] : []),
      ...(dropoff ? [dropoff] : []),
      ...segments.flatMap((s) => s.coordinates),
    ].filter((p) => p && Number.isFinite(p.latitude) && Number.isFinite(p.longitude));

    if (allPoints.length === 0 || !mapRef.current) return;
    const timeout = setTimeout(() => {
      try {
        mapRef.current?.fitToCoordinates(allPoints, {
          edgePadding: { top: 80, right: 60, bottom: 260, left: 60 },
          animated: true,
        });
      } catch {
        // el mapa puede no estar listo todavía; se ignora, no rompe la UI
      }
    }, 200);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);

  const initialRegion: Region = {
    latitude: currentLocation.latitude,
    longitude: currentLocation.longitude,
    latitudeDelta: 0.08,
    longitudeDelta: 0.08,
  };

  return (
    <View style={StyleSheet.absoluteFill}>
      <MapView ref={mapRef} style={StyleSheet.absoluteFill} initialRegion={initialRegion}>
        {directSegment && directSegment.coordinates.length > 1 && (
          <Polyline
            coordinates={directSegment.coordinates}
            strokeColor={colors.routeDirect}
            strokeWidth={3}
            lineDashPattern={[6, 6]}
          />
        )}

        {segments.map((seg, idx) =>
          seg.coordinates.length > 1 ? (
            <Polyline
              key={`${seg.type}-${idx}`}
              coordinates={seg.coordinates}
              strokeColor={SEGMENT_COLOR[seg.type] || colors.primary}
              strokeWidth={5}
            />
          ) : null
        )}

        <Marker coordinate={destination} anchor={{ x: 0.5, y: 1 }} zIndex={5}>
          <View style={[styles.pin, { backgroundColor: colors.navy }]}>
            <Ionicons name="flag" size={16} color="white" />
          </View>
        </Marker>

        {pickup && (
          <Marker coordinate={pickup} anchor={{ x: 0.5, y: 1 }} zIndex={4}>
            <View style={[styles.pin, { backgroundColor: colors.primary }]}>
              <Ionicons name="restaurant" size={15} color="white" />
            </View>
          </Marker>
        )}

        {dropoff && (
          <Marker coordinate={dropoff} anchor={{ x: 0.5, y: 1 }} zIndex={4}>
            <View style={[styles.pin, { backgroundColor: colors.green }]}>
              <Ionicons name="cube" size={15} color="white" />
            </View>
          </Marker>
        )}

        {incidentPoint && (
          <Marker coordinate={incidentPoint} anchor={{ x: 0.5, y: 1 }} zIndex={6}>
            <View style={[styles.pin, { backgroundColor: colors.red }]}>
              <Ionicons name="alert" size={14} color="white" />
            </View>
          </Marker>
        )}

        {vehiclePosition && (
          <Marker coordinate={vehiclePosition} anchor={{ x: 0.5, y: 0.5 }} zIndex={10}>
            <View style={styles.vehicleDot}>
              <Ionicons name={vehicleIcon} size={16} color="white" />
            </View>
          </Marker>
        )}
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  pin: {
    width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center",
    borderWidth: 2, borderColor: "white",
    shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
  },
  vehicleDot: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: colors.primary,
    alignItems: "center", justifyContent: "center", borderWidth: 3, borderColor: "white",
    shadowColor: "#000", shadowOpacity: 0.3, shadowRadius: 5, shadowOffset: { width: 0, height: 2 },
  },
});
