import React from "react";
import { View } from "react-native";
import { LoadingOverlay } from "../components/LoadingOverlay";
import { OrderCard } from "../components/OrderCard";
import { RouteLegend } from "../components/RouteLegend";
import { RouteMap } from "../components/RouteMap";
import { colors } from "../constants/theme";
import { useSessionContext } from "../context/SessionContext";
import { makeSegment } from "../utils/routeHelpers";

export default function RecommendationScreen() {
  const { config, offers, offerIndex, currentOffer, busy, appState, actions } = useSessionContext();

  if (!config || !currentOffer) return null;

  const previewSegments =
    currentOffer.status === "available"
      ? [
          makeSegment("to_pickup", config.currentLocation, currentOffer.pickup, 30),
          makeSegment("to_dropoff", currentOffer.pickup, currentOffer.dropoff, 30),
          makeSegment("to_destination", currentOffer.dropoff, config.destination, 30),
        ]
      : [];
  const directSegment = makeSegment("direct", config.currentLocation, config.destination, 30);

  return (
    <View style={{ flex: 1 }}>
      <RouteMap
        currentLocation={config.currentLocation}
        destination={config.destination}
        pickup={currentOffer.status === "available" ? currentOffer.pickup : null}
        dropoff={currentOffer.status === "available" ? currentOffer.dropoff : null}
        segments={previewSegments}
        directSegment={directSegment}
        vehiclePosition={config.currentLocation}
        fitKey={currentOffer.id}
      />
      <RouteLegend
        items={[
          { color: colors.routeToPickup, label: "To pickup" },
          { color: colors.routeToDropoff, label: "To drop-off" },
          { color: colors.routeToDestination, label: "To destination" },
        ]}
      />

      <OrderCard
        offer={currentOffer}
        isBestMatch={offerIndex === 0}
        canGoPrevious={offerIndex > 0}
        canGoNext={offerIndex < offers.length - 1}
        busy={busy || appState === "confirming_order"}
        onAccept={actions.acceptCurrent}
        onSkip={actions.skipCurrent}
        onPrevious={actions.goPreviousOption}
        onNext={actions.goNextOption}
        onExpired={actions.skipCurrent}
      />

      {appState === "confirming_order" && (
        <View style={{ position: "absolute", top: 60, alignSelf: "center" }}>
          <LoadingOverlay label="Confirming order…" />
        </View>
      )}
    </View>
  );
}
