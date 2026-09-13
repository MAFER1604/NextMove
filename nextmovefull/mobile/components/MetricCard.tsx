import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, radius, typography } from "../constants/theme";

interface Props {
  icon: keyof typeof Ionicons.glyphMap;
  value: string;
  label: string;
  accent?: string;
}

export function MetricCard({ icon, value, label, accent = colors.primary }: Props) {
  return (
    <View style={styles.card}>
      <View style={[styles.iconWrap, { backgroundColor: accent + "1A" }]}>
        <Ionicons name={icon} size={16} color={accent} />
      </View>
      <Text style={typography.metricValue}>{value}</Text>
      <Text style={typography.metricLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1, backgroundColor: colors.card, borderRadius: radius.md,
    padding: 14, borderWidth: 1, borderColor: colors.border,
  },
  iconWrap: {
    width: 30, height: 30, borderRadius: 10, alignItems: "center", justifyContent: "center", marginBottom: 8,
  },
});
