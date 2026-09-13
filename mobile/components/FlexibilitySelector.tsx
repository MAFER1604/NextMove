import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { FLEXIBILITY_COPY } from "../constants/config";
import { colors, radius } from "../constants/theme";
import { Flexibility } from "../types/session";

const OPTIONS: { key: Flexibility; title: string }[] = [
  { key: "strict", title: "Strict" },
  { key: "balanced", title: "Balanced" },
  { key: "flexible", title: "Flexible" },
];

export function FlexibilitySelector({ value, onChange }: { value: Flexibility; onChange: (v: Flexibility) => void }) {
  return (
    <View style={styles.column}>
      {OPTIONS.map((opt) => {
        const active = value === opt.key;
        return (
          <TouchableOpacity
            key={opt.key}
            style={[styles.card, active && styles.cardActive]}
            onPress={() => onChange(opt.key)}
            activeOpacity={0.85}
          >
            <View style={[styles.radio, active && styles.radioActive]}>
              {active && <View style={styles.radioDot} />}
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.title, active && styles.titleActive]}>{opt.title}</Text>
              <Text style={styles.desc}>{FLEXIBILITY_COPY[opt.key]}</Text>
            </View>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  column: { gap: 10 },
  card: {
    flexDirection: "row", alignItems: "center", gap: 12, padding: 14,
    borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.border, backgroundColor: colors.card,
  },
  cardActive: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  radio: {
    width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: colors.border,
    alignItems: "center", justifyContent: "center",
  },
  radioActive: { borderColor: colors.primary },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary },
  title: { fontSize: 15, fontWeight: "700", color: colors.textPrimary },
  titleActive: { color: colors.primary },
  desc: { fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
});
