import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";

export default function DropoffScreen() {
  const { activeOffer, busy, actions } = useSessionContext();
  if (!activeOffer) return null;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <View style={styles.iconCircle}>
          <Ionicons name="cube" size={30} color="white" />
        </View>
        <Text style={styles.title}>You arrived at the drop-off</Text>
        <Text style={styles.subtitle}>Order {activeOffer.orderNumber} — hand it to the customer.</Text>

        <TouchableOpacity
          style={[styles.confirmBtn, busy && styles.confirmDisabled]}
          onPress={actions.confirmDropoff}
          disabled={busy}
        >
          <Text style={styles.confirmText}>Confirm delivery</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, padding: 24, justifyContent: "center", alignItems: "center" },
  iconCircle: {
    width: 64, height: 64, borderRadius: 32, backgroundColor: colors.green,
    alignItems: "center", justifyContent: "center", marginBottom: 18,
  },
  title: { ...typography.h1, marginBottom: 8, textAlign: "center" },
  subtitle: { ...typography.bodyMuted, marginBottom: 30, textAlign: "center" },
  confirmBtn: {
    width: "100%", backgroundColor: colors.green, borderRadius: radius.pill,
    paddingVertical: 17, alignItems: "center",
  },
  confirmDisabled: { opacity: 0.5 },
  confirmText: { color: "white", fontWeight: "800", fontSize: 15.5 },
});
