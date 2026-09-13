import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { MetricCard } from "../components/MetricCard";
import { colors, radius, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";
import { formatClock, formatKm, formatMxn } from "../utils/formatters";

export default function SessionSummaryScreen() {
  const { totals, config, arrivedOnTime, simTime, actions } = useSessionContext();
  if (!totals || !config) return null;

  const durationMin = Math.round((new Date(simTime ?? Date.now()).getTime() - new Date(totals.startedAt).getTime()) / 60000);
  const hours = Math.max(durationMin / 60, 1 / 60);
  const perHour = totals.netEarnings / hours;

  const deadlineDiffMin = Math.round((new Date(simTime ?? Date.now()).getTime() - new Date(config.deadline).getTime()) / 60000);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={[styles.badge, { backgroundColor: arrivedOnTime ? colors.greenSoft : colors.amberSoft }]}>
          <Ionicons
            name={arrivedOnTime ? "checkmark-circle" : "time"}
            size={26}
            color={arrivedOnTime ? colors.green : "#92400E"}
          />
        </View>
        <Text style={styles.title}>
          {arrivedOnTime
            ? "You arrived on time"
            : `You arrived ${Math.abs(deadlineDiffMin)} minutes after your target time`}
        </Text>
        <Text style={styles.subtitle}>Arrived at {formatClock(simTime)}</Text>

        <View style={styles.grid}>
          <MetricCard icon="hourglass-outline" value={`${durationMin} min`} label="Trip duration" />
          <MetricCard icon="bag-check-outline" value={String(totals.ordersCompleted)} label="Deliveries" accent={colors.green} />
        </View>
        <View style={styles.grid}>
          <MetricCard icon="cash-outline" value={formatMxn(totals.grossEarnings)} label="Gross income" accent={colors.amber} />
          <MetricCard icon="wallet-outline" value={formatMxn(totals.netEarnings)} label="Net earnings" accent={colors.primary} />
        </View>
        <View style={styles.grid}>
          <MetricCard icon="trending-up-outline" value={`${Math.round(perHour)} MXN/hr`} label="Earnings per hour" />
          <MetricCard icon="speedometer-outline" value={formatKm(totals.distanceKm)} label="Distance covered" />
        </View>
        <View style={styles.grid}>
          <MetricCard icon="shield-checkmark-outline" value={String(totals.incidentsAvoided)} label="Incidents avoided" accent={colors.green} />
          <MetricCard icon="flag-outline" value={formatClock(simTime)} label="Arrival time" accent={colors.navy} />
        </View>

        <TouchableOpacity style={styles.primaryBtn} onPress={actions.startAnotherTrip}>
          <Text style={styles.primaryText}>Start another trip</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.secondaryBtn} onPress={actions.returnHome}>
          <Text style={styles.secondaryText}>Return home</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: 24, alignItems: "center", paddingBottom: 40 },
  badge: { width: 60, height: 60, borderRadius: 30, alignItems: "center", justifyContent: "center", marginBottom: 14 },
  title: { ...typography.h1, textAlign: "center", marginBottom: 4 },
  subtitle: { ...typography.bodyMuted, marginBottom: 22 },
  grid: { flexDirection: "row", gap: 12, width: "100%", marginBottom: 12 },
  primaryBtn: {
    width: "100%", backgroundColor: colors.primary, borderRadius: radius.pill,
    paddingVertical: 17, alignItems: "center", marginTop: 16,
  },
  primaryText: { color: "white", fontWeight: "800", fontSize: 15.5 },
  secondaryBtn: { width: "100%", paddingVertical: 15, alignItems: "center", marginTop: 8 },
  secondaryText: { color: colors.textSecondary, fontWeight: "700" },
});
