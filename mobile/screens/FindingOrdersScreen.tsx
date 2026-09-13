import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useRef, useState } from "react";
import { Animated, SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { RouteMap } from "../components/RouteMap";
import { colors, radius, shadow, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";

const STEPS = [
  { icon: "search" as const, label: "Checking nearby orders" },
  { icon: "swap-horizontal" as const, label: "Comparing routes" },
  { icon: "shield-checkmark" as const, label: "Protecting your arrival time" },
];

export default function FindingOrdersScreen() {
  const { config, noOrdersFound, actions, busy } = useSessionContext();
  const [stepIndex, setStepIndex] = useState(0);
  const fade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fade, { toValue: 1, duration: 300, useNativeDriver: true }).start();
    const interval = setInterval(() => {
      setStepIndex((i) => (i + 1) % STEPS.length);
    }, 1100);
    return () => clearInterval(interval);
  }, [fade]);

  if (!config) return null;

  return (
    <View style={{ flex: 1 }}>
      <RouteMap
        currentLocation={config.currentLocation}
        destination={config.destination}
        segments={[]}
        directSegment={null}
        fitKey="finding-orders"
      />
      <SafeAreaView style={styles.overlay}>
        <Animated.View style={[styles.card, { opacity: fade }]}>
          {noOrdersFound ? (
            <>
              <Ionicons name="cafe-outline" size={26} color={colors.textSecondary} />
              <Text style={styles.title}>No orders currently fit your trip.</Text>
              <Text style={styles.subtitle}>We'll keep looking while protecting your arrival time.</Text>
              <View style={styles.actionsRow}>
                <TouchableOpacity style={styles.secondaryBtn} onPress={() => actions.runSearch()}>
                  <Text style={styles.secondaryBtnText}>Keep looking</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.primaryBtn} onPress={() => actions.headToDestination()}>
                  <Text style={styles.primaryBtnText}>Go to destination</Text>
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <>
              <Text style={styles.title}>Finding orders that fit your trip…</Text>
              <View style={styles.steps}>
                {STEPS.map((step, idx) => (
                  <View key={step.label} style={styles.stepRow}>
                    <View style={[styles.stepIcon, idx === stepIndex && styles.stepIconActive]}>
                      <Ionicons name={step.icon} size={15} color={idx === stepIndex ? "white" : colors.textSecondary} />
                    </View>
                    <Text style={[styles.stepLabel, idx === stepIndex && styles.stepLabelActive]}>{step.label}</Text>
                  </View>
                ))}
              </View>
            </>
          )}
        </Animated.View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: "flex-end" },
  card: {
    backgroundColor: colors.card, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg,
    padding: 24, ...shadow.floating,
  },
  title: { ...typography.h1, fontSize: 18, marginBottom: 4 },
  subtitle: { ...typography.bodyMuted, marginBottom: 18 },
  steps: { marginTop: 16, gap: 14 },
  stepRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  stepIcon: {
    width: 28, height: 28, borderRadius: 14, backgroundColor: colors.background,
    alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.border,
  },
  stepIconActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepLabel: { ...typography.bodyMuted },
  stepLabelActive: { color: colors.textPrimary, fontWeight: "700" },
  actionsRow: { flexDirection: "row", gap: 10, marginTop: 8 },
  secondaryBtn: {
    flex: 1, paddingVertical: 14, borderRadius: radius.pill, alignItems: "center",
    backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border,
  },
  secondaryBtnText: { color: colors.textSecondary, fontWeight: "700" },
  primaryBtn: { flex: 1, paddingVertical: 14, borderRadius: radius.pill, alignItems: "center", backgroundColor: colors.navy },
  primaryBtnText: { color: "white", fontWeight: "700" },
});
