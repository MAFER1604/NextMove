import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, shadow, typography } from "../constants/theme";
import { OrderOffer } from "../types/order";
import { formatClock, formatKm, formatMinutes, formatMxnCompact, secondsUntil } from "../utils/formatters";

interface Props {
  offer: OrderOffer;
  isBestMatch: boolean;
  canGoPrevious: boolean;
  canGoNext: boolean;
  busy?: boolean;
  onAccept: () => void;
  onSkip: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onExpired: () => void;
}

export function OrderCard({ offer, isBestMatch, canGoPrevious, canGoNext, busy, onAccept, onSkip, onPrevious, onNext, onExpired }: Props) {
  const [secondsLeft, setSecondsLeft] = useState(secondsUntil(offer.expiresAt));

  useEffect(() => {
    setSecondsLeft(secondsUntil(offer.expiresAt));
    const interval = setInterval(() => {
      const s = secondsUntil(offer.expiresAt);
      setSecondsLeft(s);
      if (s <= 0) {
        clearInterval(interval);
        onExpired();
      }
    }, 500);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offer.id, offer.expiresAt]);

  const isExpired = offer.status !== "available" || secondsLeft <= 0;
  const pct = Math.max(0, Math.min(1, secondsLeft / 60));

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        {isBestMatch && (
          <View style={styles.bestBadge}>
            <Ionicons name="sparkles" size={12} color={colors.primary} />
            <Text style={styles.bestBadgeText}>Best match</Text>
          </View>
        )}
        <View style={styles.countdown}>
          <View style={[styles.countdownBar, { width: `${pct * 100}%`, backgroundColor: pct < 0.25 ? colors.red : colors.primary }]} />
        </View>
      </View>

      {isExpired ? (
        <View style={styles.expiredBox}>
          <Ionicons name="time-outline" size={20} color={colors.textSecondary} />
          <Text style={styles.expiredText}>
            {offer.status === "taken" ? "Another courier already took this order." : "This order is no longer available."}
          </Text>
        </View>
      ) : (
        <>
          <Text style={styles.netEarnings}>+{formatMxnCompact(offer.netEarnings)} net</Text>
          <Text style={styles.grossSecondary}>{formatMxnCompact(offer.grossPay)} gross before costs</Text>

          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{formatMinutes(offer.extraMinutes)}</Text>
              <Text style={styles.statLabel}>extra time</Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{formatKm(offer.extraKm)}</Text>
              <Text style={styles.statLabel}>extra distance</Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{formatClock(offer.etaAtDestination)}</Text>
              <Text style={styles.statLabel}>arrival at destination</Text>
            </View>
          </View>

          <View style={styles.locRow}>
            <Ionicons name="restaurant-outline" size={15} color={colors.textSecondary} />
            <Text style={styles.locText}>{offer.restaurantName}</Text>
          </View>
          <View style={styles.locRow}>
            <Ionicons name="location-outline" size={15} color={colors.textSecondary} />
            <Text style={styles.locText}>Drop-off in {offer.dropoffLabel}</Text>
          </View>

          <Text style={styles.reason}>{offer.reasonShort}</Text>
        </>
      )}

      <View style={styles.navRow}>
        <TouchableOpacity onPress={onPrevious} disabled={!canGoPrevious} style={styles.navBtn}>
          <Ionicons name="chevron-back" size={18} color={canGoPrevious ? colors.textPrimary : colors.border} />
        </TouchableOpacity>
        <TouchableOpacity onPress={onSkip} style={styles.skipBtn} disabled={busy}>
          <Text style={styles.skipText}>Skip</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={onAccept} style={[styles.acceptBtn, (isExpired || busy) && styles.acceptDisabled]} disabled={isExpired || busy}>
          <Text style={styles.acceptText}>Accept order</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={onNext} disabled={!canGoNext} style={styles.navBtn}>
          <Ionicons name="chevron-forward" size={18} color={canGoNext ? colors.textPrimary : colors.border} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg,
    padding: 20, paddingBottom: 24, ...shadow.floating,
  },
  header: { marginBottom: 12 },
  bestBadge: {
    flexDirection: "row", alignSelf: "flex-start", alignItems: "center", gap: 4,
    backgroundColor: colors.primarySoft, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill, marginBottom: 10,
  },
  bestBadgeText: { color: colors.primary, fontWeight: "700", fontSize: 11.5 },
  countdown: { height: 4, backgroundColor: colors.border, borderRadius: 2, overflow: "hidden" },
  countdownBar: { height: "100%" },
  netEarnings: { fontSize: 32, fontWeight: "800", color: colors.textPrimary, marginTop: 4 },
  grossSecondary: { ...typography.caption, marginBottom: 14 },
  statsRow: { flexDirection: "row", gap: 20, marginBottom: 16 },
  stat: {},
  statValue: { fontSize: 16, fontWeight: "700", color: colors.textPrimary },
  statLabel: { ...typography.caption, marginTop: 1 },
  locRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 },
  locText: { ...typography.bodyMuted },
  reason: { ...typography.bodyMuted, marginTop: 10, marginBottom: 4, fontStyle: "italic" },
  expiredBox: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 22 },
  expiredText: { ...typography.body, flex: 1, color: colors.textSecondary },
  navRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 18 },
  navBtn: { width: 40, height: 48, alignItems: "center", justifyContent: "center" },
  skipBtn: {
    paddingHorizontal: 18, height: 48, borderRadius: radius.pill, alignItems: "center", justifyContent: "center",
    backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border,
  },
  skipText: { color: colors.textSecondary, fontWeight: "700" },
  acceptBtn: {
    flex: 1, height: 48, borderRadius: radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: colors.green,
  },
  acceptDisabled: { opacity: 0.4 },
  acceptText: { color: "white", fontWeight: "800", fontSize: 15.5 },
});
