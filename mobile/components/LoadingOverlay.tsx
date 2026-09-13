import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { colors, typography } from "../constants/theme";

export function LoadingOverlay({ label = "Loading…" }: { label?: string }) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={colors.primary} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, alignItems: "center", justifyContent: "center" },
  label: { marginTop: 10, ...typography.bodyMuted },
});
