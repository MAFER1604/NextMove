import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, typography } from "../constants/theme";

export function AppHeader({ subtitle }: { subtitle?: string }) {
  return (
    <View style={styles.row}>
      <View style={styles.brandRow}>
        <View style={styles.iconWrap}>
          <Ionicons name="navigate" size={16} color="white" />
        </View>
        <Text style={styles.brand}>NextMove</Text>
      </View>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 8 },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  iconWrap: {
    width: 26, height: 26, borderRadius: 8, backgroundColor: colors.navy,
    alignItems: "center", justifyContent: "center",
  },
  brand: { ...typography.h2, fontWeight: "800" },
  subtitle: { ...typography.caption },
});
