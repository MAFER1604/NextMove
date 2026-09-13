import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";

export default function ErrorScreen() {
  const { notifications, actions } = useSessionContext();
  const message = notifications.find((n) => n.scope === "session" && n.type === "error")?.message;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Ionicons name="cloud-offline-outline" size={44} color={colors.textSecondary} />
        <Text style={styles.title}>Something went wrong</Text>
        <Text style={styles.message}>{message || "Please try again."}</Text>
        <TouchableOpacity style={styles.primaryBtn} onPress={actions.returnHome}>
          <Text style={styles.primaryText}>Start over</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, alignItems: "center", justifyContent: "center", padding: 30 },
  title: { ...typography.h1, marginTop: 16, marginBottom: 6 },
  message: { ...typography.bodyMuted, textAlign: "center", marginBottom: 26 },
  primaryBtn: { backgroundColor: colors.navy, borderRadius: radius.pill, paddingVertical: 15, paddingHorizontal: 30 },
  primaryText: { color: "white", fontWeight: "800" },
});
