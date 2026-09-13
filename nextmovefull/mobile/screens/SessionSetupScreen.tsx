import { Ionicons } from "@expo/vector-icons";
import DateTimePicker from "@react-native-community/datetimepicker";
import React, { useState } from "react";
import {
  Platform, SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View,
} from "react-native";
import { FlexibilitySelector } from "../components/FlexibilitySelector";
import { VehicleSelector } from "../components/VehicleSelector";
import { CURRENT_LOCATION_PRESETS, DESTINATION_PRESETS, PresetLocation } from "../constants/locations";
import { colors, radius, typography } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";
import { useLocation } from "../hooks/useLocation";
import { Flexibility, Vehicle } from "../types/session";
import { validateSetup } from "../utils/validators";

export default function SessionSetupScreen() {
  const { actions, busy, preferences } = useSessionContext();
  const { requestLocation, status: locationStatus } = useLocation();

  const [origin, setOrigin] = useState<PresetLocation | null>(CURRENT_LOCATION_PRESETS[0]);
  const [destination, setDestination] = useState<PresetLocation | null>(DESTINATION_PRESETS[0]);
  const [deadline, setDeadline] = useState<Date>(() => {
    const d = new Date();
    d.setHours(d.getHours() + 2, 0, 0, 0);
    return d;
  });
  const [showPicker, setShowPicker] = useState(false);
  const [flexibility, setFlexibility] = useState<Flexibility>(preferences.flexibility);
  const [vehicle, setVehicle] = useState<Vehicle>(preferences.vehicle);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleUseGps = async () => {
    const coords = await requestLocation();
    if (coords) {
      setOrigin({ id: "gps", label: "Current location", ...coords });
    }
  };

  const handleSubmit = async () => {
    const result = validateSetup({ origin, destination, deadline, vehicle });
    setErrors(result.errors);
    if (!result.valid || !origin || !destination) return;

    await actions.startSetup({
      currentLocation: { latitude: origin.latitude, longitude: origin.longitude, label: origin.label },
      destination: { latitude: destination.latitude, longitude: destination.longitude, label: destination.label },
      deadline: deadline.toISOString(),
      flexibility,
      vehicle,
    });
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={typography.h1}>Where are you heading?</Text>

        <View style={styles.field}>
          <Text style={styles.label}>Current location</Text>
          <TouchableOpacity style={styles.gpsRow} onPress={handleUseGps}>
            <Ionicons name="locate" size={16} color={colors.primary} />
            <Text style={styles.gpsText}>
              {locationStatus === "requesting" ? "Getting your location…" : "Use my GPS location"}
            </Text>
          </TouchableOpacity>
          <PresetList options={CURRENT_LOCATION_PRESETS} selectedId={origin?.id} onSelect={setOrigin} />
          {errors.origin && <Text style={styles.error}>{errors.origin}</Text>}
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Final destination</Text>
          <View style={styles.destInputRow}>
            <Ionicons name="flag" size={16} color={colors.textSecondary} />
            <Text style={styles.destInputText}>{destination?.label || "Choose a destination"}</Text>
          </View>
          <PresetList options={DESTINATION_PRESETS} selectedId={destination?.id} onSelect={setDestination} />
          {errors.destination && <Text style={styles.error}>{errors.destination}</Text>}
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Arrival deadline</Text>
          <TouchableOpacity style={styles.timeButton} onPress={() => setShowPicker(true)}>
            <Ionicons name="time-outline" size={18} color={colors.textPrimary} />
            <Text style={styles.timeText}>
              {deadline.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true })}
            </Text>
          </TouchableOpacity>
          {showPicker && (
            <DateTimePicker
              value={deadline}
              mode="time"
              display={Platform.OS === "ios" ? "spinner" : "default"}
              onChange={(_, selected) => {
                setShowPicker(Platform.OS === "ios");
                if (selected) setDeadline(selected);
              }}
            />
          )}
          {errors.deadline && <Text style={styles.error}>{errors.deadline}</Text>}
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Flexibility</Text>
          <FlexibilitySelector value={flexibility} onChange={setFlexibility} />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Vehicle</Text>
          <VehicleSelector value={vehicle} onChange={setVehicle} />
          {errors.vehicle && <Text style={styles.error}>{errors.vehicle}</Text>}
        </View>

        <TouchableOpacity style={[styles.submit, busy && styles.submitDisabled]} onPress={handleSubmit} disabled={busy}>
          <Text style={styles.submitText}>{busy ? "Finding delivery opportunities…" : "Find delivery opportunities"}</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function PresetList({
  options, selectedId, onSelect,
}: {
  options: readonly { id: string; label: string }[];
  selectedId?: string;
  onSelect: (opt: any) => void;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
      {options.map((opt) => (
        <TouchableOpacity
          key={opt.id}
          style={[styles.chip, selectedId === opt.id && styles.chipActive]}
          onPress={() => onSelect(opt)}
        >
          <Text style={[styles.chipText, selectedId === opt.id && styles.chipTextActive]}>{opt.label}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: 20, paddingBottom: 40 },
  field: { marginTop: 22 },
  label: { fontSize: 13.5, fontWeight: "700", color: colors.textPrimary, marginBottom: 10 },
  gpsRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 10 },
  gpsText: { color: colors.primary, fontWeight: "600", fontSize: 13.5 },
  destInputRow: {
    flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.card,
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: 14, marginBottom: 10,
  },
  destInputText: { ...typography.body },
  chipScroll: {},
  chip: {
    paddingHorizontal: 14, paddingVertical: 9, borderRadius: radius.pill, borderWidth: 1,
    borderColor: colors.border, backgroundColor: colors.card, marginRight: 8,
  },
  chipActive: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  chipText: { fontSize: 13, color: colors.textSecondary },
  chipTextActive: { color: colors.primary, fontWeight: "700" },
  timeButton: {
    flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.card,
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: 14,
  },
  timeText: { fontSize: 16, fontWeight: "700", color: colors.textPrimary },
  error: { color: colors.red, fontSize: 12.5, marginTop: 6 },
  submit: {
    marginTop: 34, backgroundColor: colors.navy, borderRadius: radius.pill,
    paddingVertical: 17, alignItems: "center",
  },
  submitDisabled: { opacity: 0.6 },
  submitText: { color: "white", fontWeight: "800", fontSize: 15.5 },
});
