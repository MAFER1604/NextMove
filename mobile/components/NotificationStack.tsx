import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { colors, radius, shadow, typography } from "../constants/theme";
import { AppNotification, NotificationType } from "../types/notification";

const STYLE_BY_TYPE: Record<NotificationType, { bg: string; fg: string; icon: keyof typeof Ionicons.glyphMap }> = {
  info: { bg: colors.primarySoft, fg: colors.primary, icon: "information-circle" },
  success: { bg: colors.greenSoft, fg: colors.green, icon: "checkmark-circle" },
  warning: { bg: colors.amberSoft, fg: "#92400E", icon: "time" },
  error: { bg: colors.redSoft, fg: colors.red, icon: "alert-circle" },
};

interface Props {
  notifications: AppNotification[];
  onDismiss: (id: string) => void;
}

// Máximo visible a la vez para no amontonar la pantalla (sección 2: "no
// información amontonada"). Las más recientes se muestran primero.
const MAX_VISIBLE = 2;

export function NotificationStack({ notifications, onDismiss }: Props) {
  const insets = useSafeAreaInsets();
  const visible = notifications.slice(-MAX_VISIBLE).reverse();
  if (visible.length === 0) return null;

  return (
    <View pointerEvents="box-none" style={[styles.container, { top: insets.top + 8 }]}>
      {visible.map((n) => {
        const style = STYLE_BY_TYPE[n.type];
        return (
          <View key={n.id} style={[styles.banner, { backgroundColor: style.bg }, shadow.card]}>
            <Ionicons name={style.icon} size={18} color={style.fg} />
            <Text style={[styles.message, { color: style.fg }]} numberOfLines={3}>
              {n.message}
            </Text>
            {n.dismissible && (
              <TouchableOpacity onPress={() => onDismiss(n.id)} hitSlop={8} style={styles.closeBtn}>
                <Ionicons name="close" size={16} color={style.fg} />
              </TouchableOpacity>
            )}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { position: "absolute", left: 16, right: 16, zIndex: 1000, gap: 8 },
  banner: {
    flexDirection: "row", alignItems: "flex-start", gap: 8, padding: 12, borderRadius: radius.md,
  },
  message: { flex: 1, ...typography.body, fontSize: 13.5, fontWeight: "600" },
  closeBtn: { padding: 2 },
});
