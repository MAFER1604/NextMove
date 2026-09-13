import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, radius, shadow, typography } from "../constants/theme";

interface Item { color: string; label: string; }

export function RouteLegend({ items }: { items: Item[] }) {
  return (
    <View style={styles.container}>
      {items.map((item) => (
        <View key={item.label} style={styles.row}>
          <View style={[styles.dot, { backgroundColor: item.color }]} />
          <Text style={styles.label}>{item.label}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute", top: 12, left: 12, backgroundColor: "rgba(255,255,255,0.94)",
    borderRadius: radius.md, padding: 10, gap: 6, ...shadow.card,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  label: { ...typography.caption, fontSize: 11 },
});
