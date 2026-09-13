import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, shadow, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";

export default function PickupScreen() {
  const { activeOffer, busy, notifications, actions } = useSessionContext();
  const delayNotice = notifications.find((n) => n.scope === "delivery" && n.message.startsWith("Restaurant delay"))?.message ?? null;

  if (!activeOffer) return null;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <View style={styles.iconCircle}>
          <Ionicons name="restaurant" size={30} color="white" />
        </View>
        <Text style={styles.title}>You arrived at the pickup</Text>

        <View style={styles.infoCard}>
          <InfoRow label="Restaurant" value={activeOffer.restaurantName} />
          <InfoRow label="Order" value={activeOffer.orderNumber} />
          <InfoRow label="Prep time" value={`${activeOffer.prepTimeMin} min`} />
        </View>

        {delayNotice && (
          <View style={styles.delayBox}>
            <Ionicons name="time" size={16} color="#92400E" />
            <Text style={styles.delayText}>{delayNotice}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.confirmBtn, busy && styles.confirmDisabled]}
          onPress={actions.confirmPickup}
          disabled={busy}
        >
          <Text style={styles.confirmText}>Confirm pickup</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, padding: 24, justifyContent: "center", alignItems: "center" },
  iconCircle: {
    width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primary,
    alignItems: "center", justifyContent: "center", marginBottom: 18,
  },
  title: { ...typography.h1, marginBottom: 24, textAlign: "center" },
  infoCard: {
    width: "100%", backgroundColor: colors.card, borderRadius: radius.md, padding: 18,
    borderWidth: 1, borderColor: colors.border, marginBottom: 16, ...shadow.card,
  },
  infoRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8 },
  infoLabel: { ...typography.bodyMuted },
  infoValue: { fontWeight: "700", color: colors.textPrimary },
  delayBox: {
    flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.amberSoft,
    borderRadius: radius.md, padding: 12, width: "100%", marginBottom: 16,
  },
  delayText: { color: "#92400E", flex: 1, fontSize: 13 },
  confirmBtn: {
    width: "100%", backgroundColor: colors.green, borderRadius: radius.pill,
    paddingVertical: 17, alignItems: "center", marginTop: 8,
  },
  confirmDisabled: { opacity: 0.5 },
  confirmText: { color: "white", fontWeight: "800", fontSize: 15.5 },
});
