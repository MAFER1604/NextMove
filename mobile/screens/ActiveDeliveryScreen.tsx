import { Ionicons } from "@expo/vector-icons";
import React, { useMemo } from "react";
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { DeadlineAlert } from "../components/DeadlineAlert";
import { RouteMap } from "../components/RouteMap";
import { colors, radius, shadow, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";
import { useRouteAnimation } from "../hooks/useRouteAnimation";
import { formatClock, formatMinutes, formatMxnCompact } from "../utils/formatters";

const VEHICLE_ICON = { bike: "bicycle", moto: "bicycle-outline", car: "car" } as const;

export default function ActiveDeliveryScreen() {
  const { appState, config, activeOffer, route, routeElapsedMin, totals, simTime, actions } = useSessionContext();

  const segments = route?.segments ?? [];
  const vehiclePosition = useRouteAnimation(segments, routeElapsedMin);

  const stageIndex = appState === "to_pickup" ? 0 : appState === "to_dropoff" ? 1 : 2;
  const totalMin = useMemo(() => segments.reduce((s, seg) => s + seg.durationMin, 0) || 1, [segments]);
  const progressPct = Math.min(routeElapsedMin / totalMin, 1);

  const instruction =
    appState === "to_pickup" ? "Head to pickup"
    : appState === "to_dropoff" ? "Deliver the order"
    : "Continue to your destination";

  const nextPointLabel =
    appState === "to_pickup" ? activeOffer?.restaurantName ?? "Pickup"
    : appState === "to_dropoff" ? `Drop-off in ${activeOffer?.dropoffLabel ?? ""}`
    : config?.destination.label ?? "Destination";

  const minutesRemaining = Math.max(Math.round(totalMin - routeElapsedMin), 0);
  const nowIso = simTime ?? new Date().toISOString();
  const etaDate = new Date(new Date(nowIso).getTime() + minutesRemaining * 60000);
  const finalEta = formatClock(etaDate.toISOString());

  const minutesToDeadline = config ? (new Date(config.deadline).getTime() - new Date(nowIso).getTime()) / 60000 : Infinity;
  const closeToDeadline = minutesToDeadline < 8 && minutesToDeadline > -30;

  if (!config) return null;

  return (
    <View style={{ flex: 1 }}>
      <RouteMap
        currentLocation={config.currentLocation}
        destination={config.destination}
        pickup={activeOffer?.pickup}
        dropoff={activeOffer?.dropoff}
        segments={segments}
        vehiclePosition={vehiclePosition}
        vehicleIcon={VEHICLE_ICON[config.vehicle]}
        fitKey={appState + (activeOffer?.id ?? "direct")}
      />

      <SafeAreaView style={styles.topOverlay} pointerEvents="box-none">
        <View style={styles.instructionPill}>
          <Ionicons name="navigate" size={14} color="white" />
          <Text style={styles.instructionText}>{instruction}</Text>
        </View>
        {closeToDeadline && <DeadlineAlert message="Your arrival time is coming up soon." />}
      </SafeAreaView>

      <View style={styles.bottomCard}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progressPct * 100}%` }]} />
        </View>

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.nextLabel}>Next</Text>
            <Text style={styles.nextValue}>{nextPointLabel}</Text>
          </View>
          <View style={{ alignItems: "flex-end" }}>
            <Text style={styles.nextLabel}>ETA destination</Text>
            <Text style={styles.nextValue}>{finalEta}</Text>
          </View>
        </View>

        <View style={styles.row}>
          <Text style={styles.metaText}>{formatMinutes(minutesRemaining)} to next point</Text>
          <Text style={styles.metaText}>{formatMxnCompact(totals?.netEarnings ?? 0)} earned so far</Text>
        </View>

        {appState === "to_destination" && (
          <Text style={styles.headingMessage}>Time to head to your destination</Text>
        )}

        <Text style={styles.safety}>Only interact when safely stopped.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  topOverlay: { position: "absolute", top: 0, left: 0, right: 0, alignItems: "center", gap: 8 },
  instructionPill: {
    flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.navy,
    paddingHorizontal: 16, paddingVertical: 10, borderRadius: radius.pill, marginTop: 10, ...shadow.card,
  },
  instructionText: { color: "white", fontWeight: "700", fontSize: 13.5 },
  bottomCard: {
    position: "absolute", left: 0, right: 0, bottom: 0, backgroundColor: colors.card,
    borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: 20, ...shadow.floating,
  },
  progressTrack: { height: 4, backgroundColor: colors.border, borderRadius: 2, overflow: "hidden", marginBottom: 16 },
  progressFill: { height: "100%", backgroundColor: colors.primary },
  row: { flexDirection: "row", justifyContent: "space-between", marginBottom: 10 },
  nextLabel: { ...typography.caption },
  nextValue: { fontSize: 15.5, fontWeight: "700", color: colors.textPrimary, marginTop: 2 },
  metaText: { ...typography.bodyMuted, fontSize: 12.5 },
  headingMessage: { ...typography.body, fontWeight: "700", marginTop: 8, color: colors.navy },
  safety: { ...typography.caption, textAlign: "center", marginTop: 14 },
});
