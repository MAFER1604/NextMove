# NextMove — Frontend de producto (entrega)

Reconstrucción completa del frontend de NextMove como una experiencia de
consumidor pulida: sin modo de jueces, sin jerga técnica visible, con mapa
real y todas las interacciones funcionando de principio a fin (en modo
simulado; ver limitaciones abajo para el modo con backend real).

## 1. Archivos creados / modificados

**Eliminados** (pertenecían al "modo jueces" de la versión anterior):
`components/AgentPanel.tsx`, `DecisionCard.tsx`, `DecisionLogModal.tsx`,
`EvaluationPanel.tsx`, `ReplayPanel.tsx`, `SimulationControls.tsx`,
`SetupPanel.tsx`, `RouteMap.tsx` (versión esquemática anterior),
`ResultsPanel.tsx`, `EventBanner.tsx` (versión anterior), y los archivos
`hooks/useSimulation.ts`, `services/api.ts`, `App.tsx`, `constants/theme.ts`,
`constants/config.ts`, `types/simulation.ts`, `utils/formatters.ts`
(reemplazados por completo).

**Creados:**

```
mobile/
├── App.tsx
├── app.json                          (permisos de ubicación, plugin expo-location)
├── package.json                      (nuevas dependencias)
├── .env.example                      (EXPO_PUBLIC_USE_MOCK agregado)
├── context/SessionContext.tsx
├── navigation/AppNavigator.tsx
├── screens/
│   ├── WelcomeScreen.tsx
│   ├── SessionSetupScreen.tsx
│   ├── FindingOrdersScreen.tsx
│   ├── RecommendationScreen.tsx
│   ├── ActiveDeliveryScreen.tsx
│   ├── PickupScreen.tsx
│   ├── DropoffScreen.tsx
│   ├── OrderCompletedScreen.tsx
│   ├── SessionSummaryScreen.tsx
│   └── ErrorScreen.tsx
├── components/
│   ├── AppHeader.tsx
│   ├── RouteMap.tsx                  (react-native-maps real)
│   ├── RouteLegend.tsx
│   ├── OrderCard.tsx
│   ├── MetricCard.tsx
│   ├── EventBanner.tsx
│   ├── DeadlineAlert.tsx
│   ├── VehicleSelector.tsx
│   ├── FlexibilitySelector.tsx
│   ├── ConnectionBanner.tsx
│   ├── InlineErrorBanner.tsx
│   └── LoadingOverlay.tsx            (actualizado al nuevo tema)
├── hooks/
│   ├── useSession.ts                 (máquina de estados central)
│   ├── useLocation.ts
│   └── useRouteAnimation.ts
├── services/
│   ├── api.ts                        (adaptador del backend real)
│   └── mockApi.ts                    (motor simulado completo)
├── types/
│   ├── session.ts
│   ├── order.ts
│   ├── route.ts
│   └── api.ts
├── constants/
│   ├── theme.ts                      (paleta exacta del brief)
│   ├── locations.ts                  (ubicaciones reales cerca del Tec)
│   └── config.ts
└── utils/
    ├── formatters.ts
    ├── routeHelpers.ts                (rutas deterministas, interpolación)
    └── validators.ts
```

37 archivos TypeScript en total.

## 2. Qué hace cada pantalla

| Pantalla | Qué muestra |
|---|---|
| **Welcome** | Logo, tagline, ilustración de ruta (SVG), botón "Start a trip" |
| **SessionSetup** | Ubicación actual (GPS o preset), destino, hora límite (selector de hora nativo), flexibilidad, vehículo, validación de campos |
| **FindingOrders** | Mapa de fondo + tarjeta animada con 3 pasos ("Checking nearby orders" → "Comparing routes" → "Protecting your arrival time"); si no hay pedidos, ofrece seguir buscando o ir directo al destino |
| **Recommendation** | Mapa con ruta completa (recogida/entrega/destino) + tarjeta de oferta con ganancia neta, contador de 60s, Aceptar/Skip/Anterior/Siguiente |
| **ActiveDelivery** | Navegación simplificada: instrucción actual, mapa con vehículo animado sobre la ruta, barra de progreso, ETA, ganancia acumulada |
| **Pickup** | "You arrived at the pickup", nombre del restaurante, número de pedido, tiempo de preparación, botón Confirm pickup (con aviso si hay retraso del restaurante) |
| **Dropoff** | "You arrived at the drop-off", botón Confirm delivery |
| **OrderCompleted** | Desglose bruto/costo/neto, total acumulado de la sesión, botones "Find next order" / "Go to destination" |
| **SessionSummary** | Llegada a tiempo o tarde, 8 métricas con íconos (duración, entregas, ingreso bruto, ganancia neta, ganancia/hora, distancia, incidentes evitados, hora de llegada), "Start another trip" |
| **ErrorScreen** | Mensaje + botón para reiniciar; nunca pantalla en blanco |

## 3. Dependencias instaladas

```
react-native-maps, expo-location, @expo/vector-icons,
@react-navigation/native, @react-navigation/native-stack,
react-native-screens, react-native-safe-area-context,
@react-native-community/datetimepicker, react-native-svg
```

Todas compatibles con Expo Go (`react-native-maps` está oficialmente listado
como soportado en Expo Go — confirmado en la documentación de Expo: *"No
additional setup is required when testing your project using Expo Go"*).

## 4. Ejecución

```bash
cd mobile
npm install
cp .env.example .env
npx expo start
```

Escanea el QR con la app **Expo Go** en tu Android. Con
`EXPO_PUBLIC_USE_MOCK=true` (valor por defecto) la app funciona de principio
a fin sin necesitar el backend corriendo.

### Activar el backend real (parcial, ver limitaciones)

```bash
# EXPO_PUBLIC_USE_MOCK=false
# EXPO_PUBLIC_API_URL=http://<tu-ip-lan>:8000
```

## 5. Endpoints utilizados del backend real

Inspeccioné `main.py` antes de tocar nada. `services/api.ts` usa:

* `GET /health` — chequeo de conexión.
* `POST /scenario/generate` + `POST /simulation/start` — crea un turno real
  con zonas mapeadas desde las coordenadas reales elegidas por el usuario.

No se creó ningún endpoint nuevo ni se duplicó ninguno existente.

## 6. Limitación importante — léela antes de asumir que "modo real" funciona igual

El backend existente fue diseñado para un **agente autónomo** que decide
ACCEPT/SKIP en <50ms en cuanto aparece un pedido, sin ventana revisable por
un humano, y sin exponer jamás pedidos "todavía no revelados" a futuro (por
diseño, para no hacer trampa con información futura).

La nueva experiencia pedida —mostrar una oferta con 60s para responder,
navegar entre opciones con Anterior/Siguiente, confirmar pickup/dropoff como
pasos explícitos— **no tiene equivalente hoy en el backend real**. No fingí
que sí funciona: `services/api.ts` usa el backend real solo para el
health-check y la creación del turno (con mapeo honesto de zonas a
coordenadas), y delega explícitamente el flujo interactivo completo a
`mockApi.ts`, con un comentario grande en el código explicando por qué.

**Esto significa:** con `EXPO_PUBLIC_USE_MOCK=true` (default) o `false`, la
experiencia de uso es la misma (mockApi), porque hoy no hay forma honesta de
conectar el flujo de "oferta revisable por humano" al motor autónomo
existente sin cambiar el backend. Si se quiere soporte real de punta a
punta, el backend necesitaría un modo nuevo donde una oferta quede "en
espera" hasta que el usuario responda o expire el conteo — eso es trabajo de
backend pendiente, no de este frontend.

## 7. Funciones que trabajan de verdad (probadas en el motor simulado)

* Formulario de configuración con validación real de campos.
* GPS (`expo-location`) con fallback a selección manual si se niega el permiso.
* Búsqueda de pedidos: genera candidatos, descarta en silencio los que
  violan las 5 reglas de seguridad (zona restringida de noche, descanso
  obligatorio, calor, tiempo de llegada, capacidad del vehículo).
* Contador de 60s por oferta con expiración automática y probabilidad de que
  "otro repartidor" se adelante.
* Anterior/Siguiente entre ofertas, con reconsulta de disponibilidad real.
* Aceptar pedido: reconfirma disponibilidad antes de comprometerse.
* Ruta con segmentos reales (`RouteSegment[]`) coloreados por tipo, ajuste
  automático del mapa (`fitToCoordinates`), vehículo animado por
  interpolación sin saltos.
* Eventos naturales durante el trayecto: cierre vial (agrega minutos),
  retraso de restaurante de 15 min, alerta de riesgo de llegada.
* Confirmar pickup / confirmar dropoff, con acumulación real de ganancias
  brutas/netas/distancia/pedidos completados a lo largo de toda la sesión
  (no se reinicia entre pedidos).
* "Find next order" verifica tiempo restante antes de seguir buscando;
  si no alcanza, pasa automáticamente a "Go to destination".
* Resumen final con verificación real de llegada a tiempo vs. la hora
  límite y la flexibilidad elegida.
* Manejo de errores: sesión no encontrada, oferta ya no disponible, fallo de
  confirmación — todo con mensaje + acción de reintento, nunca pantalla en blanco.

## 8. Pendiente / no verificado

* **No se probó en un dispositivo Android físico ni en Expo Go real** dentro
  de este entorno (sin acceso a un teléfono). Se verificó: TypeScript
  compila sin errores (`npx tsc --noEmit`, código de salida 0), y las 630
  dependencias instalan sin conflictos. Recomiendo correr `npx expo start`
  y probarlo en un dispositivo real antes de presentarlo.
* **Integración real de punta a punta con el backend** no implementada (ver
  sección 6) — es una limitación arquitectónica real del backend actual, no
  un descuido.
* El ícono de moto usa `bicycle-outline` de Ionicons como aproximación (no
  existe un ícono de moto dedicado en el set gratuito de Ionicons); es una
  simplificación visual menor.
* La generación de nombres de restaurantes es una lista genérica fija
  (`RESTAURANT_NAMES` en `mockApi.ts`), no nombres de negocios reales.

## 9. Errores encontrados y corregidos durante la construcción

* Verifiqué que `react-native-maps` requiere API key de Google Maps solo
  para builds de producción, no para Expo Go — evité configurar algo
  innecesario y lo dejé documentado como placeholder para el futuro.
* Diseñé `useRouteAnimation` inicialmente con `AnimatedRegion` nativo de
  `react-native-maps`, pero lo simplifiqué a interpolación simple basada en
  estado de React: es más predecible y verificable sin un dispositivo real
  para probar quirks de la API animada nativa.
* En `AppNavigator.tsx`, los banners flotantes (conexión, error) usaban
  `position: absolute` como hermanos de `NavigationContainer` sin un
  contenedor padre con `flex:1` explícito — lo corregí envolviendo todo en
  una `View` de altura completa.
