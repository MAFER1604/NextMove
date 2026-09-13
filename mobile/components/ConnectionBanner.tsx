import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, typography } from "../constants/theme";

interface Props {
  connected: boolean | null;
  isMock: boolean;
  onRetry: () => void;
}

export function ConnectionBanner({ connected, isMock, onRetry }: Props) {
  if (connected !== false) return null; // null = todavía verificando; true = no mostrar nada

  // Con datos simulados, no poder alcanzar el backend real no rompe nada.
  // Sin ellos, es un problema real que el usuario debe saber y poder reintentar
  // (sección 19: nunca continuar en silencio con información incompleta).
  if (isMock) {
    return (
      <View style={styles.container}>
        <Ionicons name="cloud-offline-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.text}>Using on-device data right now — everything still works.</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, styles.containerWarning]}>
      <Ionicons name="warning-outline" size={14} color={colors.red} />
      <Text style={[styles.text, styles.textWarning]}>Can't reach the server right now.</Text>
      <TouchableOpacity onPress={onRetry} hitSlop={8}>
        <Text style={styles.retry}>Retry</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row", alignItems: "center", gap: 6, justifyContent: "center",
    paddingVertical: 6, backgroundColor: colors.background,
  },
  containerWarning: { backgroundColor: colors.redSoft },
  text: { ...typography.caption, fontSize: 11 },
  textWarning: { color: colors.red, fontWeight: "600" },
  retry: { color: colors.red, fontWeight: "800", fontSize: 11, marginLeft: 4, textDecorationLine: "underline" },
});
