import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius } from "../constants/theme";
import { Vehicle } from "../types/session";

const OPTIONS: { key: Vehicle; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "bike", label: "Bike", icon: "bicycle" },
  { key: "moto", label: "Moto", icon: "bicycle-outline" },
  { key: "car", label: "Car", icon: "car" },
];

export function VehicleSelector({ value, onChange }: { value: Vehicle; onChange: (v: Vehicle) => void }) {
  return (
    <View style={styles.row}>
      {OPTIONS.map((opt) => {
        const active = value === opt.key;
        return (
          <TouchableOpacity
            key={opt.key}
            style={[styles.option, active && styles.optionActive]}
            onPress={() => onChange(opt.key)}
            activeOpacity={0.8}
          >
            <Ionicons name={opt.icon} size={22} color={active ? colors.primary : colors.textSecondary} />
            <Text style={[styles.label, active && styles.labelActive]}>{opt.label}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 10 },
  option: {
    flex: 1, alignItems: "center", paddingVertical: 14, borderRadius: radius.md,
    borderWidth: 1.5, borderColor: colors.border, backgroundColor: colors.card, gap: 6,
  },
  optionActive: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  label: { fontSize: 12.5, fontWeight: "600", color: colors.textSecondary },
  labelActive: { color: colors.primary },
});
