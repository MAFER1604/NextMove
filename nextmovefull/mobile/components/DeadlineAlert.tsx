import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, radius, typography } from "../constants/theme";

export function DeadlineAlert({ message }: { message: string }) {
  return (
    <View style={styles.container}>
      <Ionicons name="alert-circle" size={18} color={colors.red} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.redSoft,
    borderRadius: radius.md, padding: 12, marginHorizontal: 16, marginTop: 8,
  },
  text: { ...typography.body, color: colors.red, fontWeight: "600", flex: 1 },
});
