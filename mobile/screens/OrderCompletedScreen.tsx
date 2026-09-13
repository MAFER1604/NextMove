import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useRef } from "react";
import { Animated, SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, shadow, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";
import { formatMinutes, formatMxn, formatMxnCompact } from "../utils/formatters";

export default function OrderCompletedScreen() {
  const { lastCompleted, totals, busy, actions } = useSessionContext();
  const scale = useRef(new Animated.Value(0.7)).current;

  useEffect(() => {
    Animated.spring(scale, { toValue: 1, friction: 5, useNativeDriver: true }).start();
  }, [scale]);

  if (!lastCompleted || !totals) return null;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Animated.View style={[styles.successCircle, { transform: [{ scale }] }]}>
          <Ionicons name="checkmark" size={34} color="white" />
        </Animated.View>
        <Text style={styles.title}>Delivery completed</Text>

        <View style={styles.card}>
          <Row label="Gross pay" value={formatMxn(lastCompleted.grossPay)} />
          <Row label="Estimated cost" value={`-${formatMxnCompact(lastCompleted.cost)}`} />
          <View style={styles.divider} />
          <Row label="Net earnings" value={formatMxn(lastCompleted.netEarnings)} bold />
          <Row label="Time used" value={formatMinutes(lastCompleted.minutesUsed)} />
        </View>

        <Text style={styles.sessionTotal}>Session total: {formatMxn(totals.netEarnings)}</Text>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.secondaryBtn} onPress={actions.headToDestination} disabled={busy}>
            <Text style={styles.secondaryText}>Go to destination</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.primaryBtn} onPress={actions.findNextOrder} disabled={busy}>
            <Text style={styles.primaryText}>Find next order</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, bold && styles.rowValueBold]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, padding: 24, justifyContent: "center", alignItems: "center" },
  successCircle: {
    width: 68, height: 68, borderRadius: 34, backgroundColor: colors.green,
    alignItems: "center", justifyContent: "center", marginBottom: 16,
  },
  title: { ...typography.h1, marginBottom: 22 },
  card: {
    width: "100%", backgroundColor: colors.card, borderRadius: radius.md, padding: 18,
    borderWidth: 1, borderColor: colors.border, ...shadow.card,
  },
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 7 },
  rowLabel: { ...typography.bodyMuted },
  rowValue: { fontWeight: "600", color: colors.textPrimary },
  rowValueBold: { fontSize: 17, fontWeight: "800" },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: 6 },
  sessionTotal: { ...typography.body, fontWeight: "700", marginTop: 20, marginBottom: 26 },
  actions: { flexDirection: "row", gap: 10, width: "100%" },
  secondaryBtn: {
    flex: 1, paddingVertical: 15, borderRadius: radius.pill, alignItems: "center",
    backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border,
  },
  secondaryText: { color: colors.textSecondary, fontWeight: "700" },
  primaryBtn: { flex: 1, paddingVertical: 15, borderRadius: radius.pill, alignItems: "center", backgroundColor: colors.primary },
  primaryText: { color: "white", fontWeight: "800" },
});
