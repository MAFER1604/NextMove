import { NavigationContainer, useNavigation } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React, { useEffect } from "react";
import { View } from "react-native";
import { ConnectionBanner } from "../components/ConnectionBanner";
import { NotificationStack } from "../components/NotificationStack";
import { useSessionContext } from "../context/SessionContext";
import { AppState } from "../types/session";
import ActiveDeliveryScreen from "../screens/ActiveDeliveryScreen";
import DropoffScreen from "../screens/DropoffScreen";
import ErrorScreen from "../screens/ErrorScreen";
import FindingOrdersScreen from "../screens/FindingOrdersScreen";
import OrderCompletedScreen from "../screens/OrderCompletedScreen";
import PickupScreen from "../screens/PickupScreen";
import RecommendationScreen from "../screens/RecommendationScreen";
import SessionSetupScreen from "../screens/SessionSetupScreen";
import SessionSummaryScreen from "../screens/SessionSummaryScreen";
import WelcomeScreen from "../screens/WelcomeScreen";

const Stack = createNativeStackNavigator();

// Solo los estados que deben disparar navegación automática. "setup" se
// resuelve aparte, vía postResetTarget (Welcome la primera vez / tras
// "Return home", SessionSetup tras "Start another trip").
function screenForState(appState: AppState, arrivedAtStop: boolean): string | null {
  switch (appState) {
    case "searching":
    case "searching_next":
      return "FindingOrders";
    case "reviewing_offer":
    case "confirming_order":
      return "Recommendation";
    case "to_pickup":
      return "ActiveDelivery";
    case "waiting_pickup":
      return "Pickup";
    case "to_dropoff":
      return arrivedAtStop ? "Dropoff" : "ActiveDelivery";
    case "delivery_completed":
      return "OrderCompleted";
    case "to_destination":
      return "ActiveDelivery";
    case "session_completed":
      return "SessionSummary";
    case "error":
      return "ErrorScreen";
    default:
      return null; // "setup"
  }
}

function StateRouter() {
  const navigation = useNavigation<any>();
  const { appState, arrivedAtStop, postResetTarget, actions } = useSessionContext();

  // Navegación disparada por la máquina de estados de la sesión (búsqueda,
  // oferta, entrega, resumen, error).
  useEffect(() => {
    const target = screenForState(appState, arrivedAtStop);
    if (target) {
      navigation.reset({ index: 0, routes: [{ name: target }] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appState, arrivedAtStop]);

  // Navegación disparada explícitamente por resetSession() ("Start another
  // trip" / "Return home"): usa un reset de stack real, no un simple
  // navigate(), para que el botón atrás no pueda regresar a la pantalla
  // anterior (SessionSummary u otra) — sección 16/17 del brief.
  useEffect(() => {
    if (postResetTarget) {
      navigation.reset({ index: 0, routes: [{ name: postResetTarget }] });
      actions.consumePostResetTarget();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postResetTarget]);

  return null;
}

export function AppNavigator() {
  const { connected, isMock, notifications, actions } = useSessionContext();

  return (
    <View style={{ flex: 1 }}>
      <NavigationContainer>
        <StateRouter />
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Welcome" component={WelcomeScreen} />
          <Stack.Screen name="SessionSetup" component={SessionSetupScreen} />
          <Stack.Screen name="FindingOrders" component={FindingOrdersScreen} />
          <Stack.Screen name="Recommendation" component={RecommendationScreen} />
          <Stack.Screen name="ActiveDelivery" component={ActiveDeliveryScreen} />
          <Stack.Screen name="Pickup" component={PickupScreen} />
          <Stack.Screen name="Dropoff" component={DropoffScreen} />
          <Stack.Screen name="OrderCompleted" component={OrderCompletedScreen} />
          <Stack.Screen name="SessionSummary" component={SessionSummaryScreen} />
          <Stack.Screen name="ErrorScreen" component={ErrorScreen} />
        </Stack.Navigator>
      </NavigationContainer>
      <ConnectionBanner connected={connected} isMock={isMock} onRetry={actions.retryConnection} />
      <NotificationStack notifications={notifications} onDismiss={actions.dismissNotification} />
    </View>
  );
}
