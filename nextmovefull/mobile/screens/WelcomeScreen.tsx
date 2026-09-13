import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React from "react";
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import Svg, { Circle, Path } from "react-native-svg";
import { colors, radius, typography } from "../constants/theme";

function RouteIllustration() {
  return (
    <Svg width={220} height={140} viewBox="0 0 220 140">
      <Path
        d="M20 120 C 60 120, 60 40, 110 40 S 160 100, 200 20"
        stroke={colors.border}
        strokeWidth={4}
        fill="none"
        strokeDasharray="2 10"
        strokeLinecap="round"
      />
      <Circle cx="20" cy="120" r="7" fill={colors.primary} />
      <Circle cx="110" cy="40" r="6" fill={colors.green} />
      <Circle cx="200" cy="20" r="7" fill={colors.navy} />
    </Svg>
  );
}

export default function WelcomeScreen() {
  const navigation = useNavigation<any>();

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <View style={styles.top}>
          <View style={styles.logo}>
            <Ionicons name="navigate" size={26} color="white" />
          </View>
          <Text style={styles.brand}>NextMove</Text>
          <Text style={styles.tagline}>Earn along the way. Arrive on time.</Text>
        </View>

        <View style={styles.illustrationWrap}>
          <RouteIllustration />
        </View>

        <View style={styles.bottom}>
          <Text style={styles.headline}>Make your next trip more valuable.</Text>
          <Text style={styles.body}>
            Find delivery opportunities that fit your route and protect your arrival time.
          </Text>
          <TouchableOpacity style={styles.cta} onPress={() => navigation.navigate("SessionSetup")} activeOpacity={0.85}>
            <Text style={styles.ctaText}>Start a trip</Text>
            <Ionicons name="arrow-forward" size={18} color="white" />
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, justifyContent: "space-between", paddingHorizontal: 28, paddingVertical: 36 },
  top: { alignItems: "center", marginTop: 12 },
  logo: {
    width: 52, height: 52, borderRadius: radius.md, backgroundColor: colors.navy,
    alignItems: "center", justifyContent: "center", marginBottom: 14,
  },
  brand: { ...typography.display, fontSize: 28 },
  tagline: { ...typography.bodyMuted, marginTop: 4 },
  illustrationWrap: { alignItems: "center", justifyContent: "center", flex: 1 },
  bottom: {},
  headline: { ...typography.h1, fontSize: 24, marginBottom: 10 },
  body: { ...typography.bodyMuted, marginBottom: 26, maxWidth: 300 },
  cta: {
    flexDirection: "row", backgroundColor: colors.primary, borderRadius: radius.pill,
    paddingVertical: 17, alignItems: "center", justifyContent: "center", gap: 8,
  },
  ctaText: { color: "white", fontWeight: "800", fontSize: 16 },
});
