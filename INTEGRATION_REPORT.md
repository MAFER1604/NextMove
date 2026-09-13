# NextMove — Diagnóstico, corrección e integración (entrega final)

## 1. Causas de los errores encontrados

| # | Causa real (confirmada leyendo el código, no supuesta) |
|---|---|
| 1 | "Start another trip" y "Return home" llamaban a la misma función `restart()`, sin distinción ni `preservePreferences`. |
| 2 | `restart()` ponía `appState="setup"`, pero `AppNavigator.screenForState()` devolvía `null` para ese estado (Welcome/Setup se navegaban a mano) — la pantalla se quedaba congelada en SessionSummary. |
| 3 | La alerta roja (`errorMessage`) se renderizaba a nivel global, por encima de TODAS las pantallas, y nada la limpiaba al avanzar de estado — solo el botón "X" manual. |
| 4 | `services/api.ts` delegaba **todo** el flujo de pedidos a `mockApi` sin importar `EXPO_PUBLIC_USE_MOCK`, porque el backend no tenía endpoints equivalentes (no existían `/app/*`). |
| 5 | Las rutas se generaban con senos/cosenos en el cliente — nunca hubo integración real con un motor de ruteo, ni en frontend ni en backend. |
| 6 | `python-dotenv` estaba en `requirements.txt` pero **nunca se llamaba** — `TOMTOM_API_KEY` jamás se habría cargado desde `.env`. |
| 7 | Proyecto en Expo SDK 51, no 57. |

## 2. Archivos modificados/creados

**Backend (nuevos):** `geo.py`, `route_provider.py`, `app_models.py`, `app_session.py`, `app_router.py`, `tests/test_app_endpoints.py`.
**Backend (modificados):** `main.py` (monta el router `/app`), `.env.example` (nota sobre TomTom).
**Frontend (reescritos):** `hooks/useSession.ts`, `hooks/useNotifications.ts` (nuevo), `navigation/AppNavigator.tsx`, `services/api.ts`, `components/ConnectionBanner.tsx`, `components/NotificationStack.tsx` (nuevo), `types/api.ts`, `types/route.ts`, `types/notification.ts` (nuevo), `package.json`, `app.json`, `.env.example`.
**Frontend (ajustes puntuales):** `screens/PickupScreen.tsx`, `screens/ErrorScreen.tsx`, `screens/ActiveDeliveryScreen.tsx`, `screens/SessionSetupScreen.tsx`, `screens/SessionSummaryScreen.tsx`, `utils/routeHelpers.ts`.
**Eliminados (obsoletos):** `components/EventBanner.tsx`, `components/InlineErrorBanner.tsx`.

## 3. Endpoints utilizados y creados

**Reutilizados sin tocar:** `POST /decide` (contrato oficial, intacto), `GET /health`.

**Creados bajo `/app` (no duplican nada existente):**
```
POST   /app/sessions
GET    /app/sessions/{id}
GET    /app/sessions/{id}/recommendations
POST   /app/sessions/{id}/orders/{order_id}/accept
POST   /app/sessions/{id}/orders/{order_id}/skip
GET    /app/sessions/{id}/route
POST   /app/sessions/{id}/advance      (no estaba en la lista original, se añadió: es lo que permite que el tiempo/posición avance realmente entre pantallas)
POST   /app/sessions/{id}/pickup
POST   /app/sessions/{id}/delivery
POST   /app/sessions/{id}/finish
DELETE /app/sessions/{id}
```
Cada sesión vive en su propia entrada de un `dict` por `session_id` — nunca una sola variable global compartida (probado en `test_two_sessions_stay_isolated`).

## 4. Cómo se obtienen las rutas ahora

`RouteProvider` → `TomTomRouteProvider` (principal) → si falla, `PrecomputedRouteProvider` (respaldo). Nunca una línea recta de 2 puntos.

**Limitación que declaro con toda honestidad:** no tengo una `TOMTOM_API_KEY` real ni acceso de red a `api.tomtom.com` desde este entorno de desarrollo. `TomTomRouteProvider` está implementado correctamente (waypoints en orden, tráfico, `departAt=now`, validación completa de la respuesta contra HTTP/rutas/legs/geometría/coordenadas), y sus pruebas unitarias usan una respuesta HTTP **simulada** para verificar el parseo — pero la conectividad real con TomTom queda sin verificar hasta correrlo con una clave real. Todo lo demás (sesión, aceptar/rechazar, pickup/delivery, aislamiento) sí corrió de extremo a extremo contra el backend real.

## 5. Evidencia de que las rutas siguen "calles" (sección 25)

Corrida real, 4 puntos de Monterrey (Origen → Pickup en Contry → Drop-off → Tec de Monterrey):

```
Provider: precomputed (sin TOMTOM_API_KEY -> cae aquí, correcto y declarado)
segmento=to_pickup        puntos= 4 distancia_km=2.67 duracion_min=6.17
segmento=to_dropoff       puntos= 4 distancia_km=3.73 duracion_min=8.60
segmento=to_destination   puntos= 4 distancia_km=0.91 duracion_min=2.11
Ultimo punto del ultimo segmento == destino final? True
Total distancia_km: 7.312 | Total duracion_min: 16.87
```
Los 4 puntos aparecen, el orden nunca cambia, cada segmento tiene 4 puntos (nunca 2 = línea recta), distancia y tiempo son > 0, y el último punto coincide exactamente con el destino final.

## 6. Resultado de `pytest`

```
51 passed, 1 warning in 1.04s
```
31 pruebas del backend de jueces (sin tocar) + 20 nuevas de `/app/*` (sesión completa, aceptar/expirar/rechazar, transiciones inválidas rechazadas con 409, aislamiento entre sesiones, TomTom simulado válido/inválido, respaldo precomputado).

## 7. Resultado de `npx tsc --noEmit`

```
exit code: 0
```
Sin errores, con Expo SDK 57 + React Native 0.86.3 + React 19.2.3 instalados.

## 8. Resultado de `npx expo-doctor`

```
19/21 checks passed. 2 checks failed.
✖ Check Expo config (app.json/ app.config.js) schema
✖ Validate packages against React Native Directory package metadata
```
**Ambos fallos son de red, no del proyecto**: expo-doctor necesita alcanzar servidores de Expo (`api.expo.dev`) para esas 2 verificaciones específicas, y este entorno de desarrollo no tiene salida a ese dominio (sí a `registry.npmjs.org`, por eso pude instalar todo). La verificación más importante — **"Check that packages match versions required by installed Expo SDK"** — sí pasó, confirmando que las versiones que fijé a mano (`expo@57.0.22`, `react-native@0.86.3`, `react@19.2.3`) son las correctas para SDK 57. Recomiendo correr `npx expo-doctor` tú mismo con conexión real antes de la entrega final, para las 2 verificaciones que no pude completar aquí.

## 9. Resultado de la prueba de la alerta (sección 27)

Verificado por lectura de código + trazado lógico (sin dispositivo real para grabarlo en vivo):
1. Una sola alerta — `useNotifications.notify()` deduplica por `message+scope`. ✅
2. Se cierra con "X" — `NotificationStack` renderiza el botón cuando `dismissible: true`. ✅
3. Desaparece sola — `autoDismissMs: 4500`. ✅
4. No reaparece sin evento nuevo — el estado vive en un hook aparte, no se recalcula en cada render. ✅
5. No aparece en Active Delivery si no corresponde — su `scope` es `"recommendation"`, distinto de `"delivery"`. ✅
6. No aparece en Session Summary — `finalizeSession()` llama `clearByScope("recommendation","delivery","session")` antes de cambiar de pantalla. ✅
7. No bloquea botones — `pointerEvents="box-none"` en el contenedor. ✅
8. Sin temporizador colgado tras cerrar sesión — `resetSession()` llama `clearAll()`, que limpia todos los `setTimeout` pendientes. ✅

## 10. Resultado de "Start another trip"

Trazado de código: `resetSession({preservePreferences:true})` → cancela el intervalo de tick (al poner `sessionId=null`), llama `DELETE /app/sessions/{id}` en el backend, limpia ofertas/ruta/métricas/notificaciones, conserva vehículo y flexibilidad, pone `appState="setup"` y `postResetTarget="SessionSetup"` → `StateRouter` ejecuta `navigation.reset()` real (no `navigate()`) hacia `SessionSetup`. Nueva sesión = nuevo `session_id`, cero entregas, cero ganancias. **No verificado en dispositivo físico.**

## 11. Resultado de "Return home"

Mismo mecanismo con `preservePreferences:false` → `postResetTarget="Welcome"`, preferencias reiniciadas a los valores por defecto. El `navigation.reset({index:0,...})` reemplaza todo el stack, así que el botón atrás físico de Android no puede regresar a SessionSummary. **No verificado en dispositivo físico.**

## 12. Comandos exactos

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # agrega tu TOMTOM_API_KEY si tienes una
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd mobile
npm install
cp .env.example .env   # ajusta EXPO_PUBLIC_API_URL a tu IP LAN
npx expo start
```
Escanea el QR con Expo Go. Con `EXPO_PUBLIC_USE_MOCK=false` (ahora el default recomendado), necesitas el backend corriendo y alcanzable.

## 13. Variables de entorno

**`backend/.env`:** `TOMTOM_API_KEY=` (opcional; sin ella cae a rutas precomputadas, nunca falla en silencio).
**`mobile/.env`:** `EXPO_PUBLIC_API_URL=http://<tu-ip-lan>:8000`, `EXPO_PUBLIC_USE_MOCK=false`.

## 14. Funciones todavía pendientes / no verificadas

- **Conectividad real con TomTom**: código correcto, sin probar contra la API en vivo (sin clave, sin acceso de red desde aquí).
- **Prueba en dispositivo/Expo Go real**: todo lo de frontend se verificó por `tsc` + trazado lógico del código, no ejecutando la app de verdad en un teléfono.
- **`npx expo-doctor`** con conexión real: 2 de 21 checks quedaron sin poder correr aquí por la misma razón de red.
- **Caché/debounce de recálculo de ruta (sección 12)**: implementé el cálculo bajo demanda, pero no el mecanismo completo de "descartar respuesta vieja si ya hay una más nueva" (no hay condición de carrera real en este modelo síncrono request/response, pero si se agrega WebSocket o polling concurrente más adelante, esto habría que revisarlo).
- **Geocodificación de direcciones escritas** (sección 10, "si se permiten"): no implementada — el proyecto solo usa ubicaciones predefinidas, que es lo mínimo exigido.
- **`prepTimeMin` y `restaurantName` en la confirmación de entrega**: el backend real no los repite en la respuesta de `/delivery`; el frontend los cachea localmente desde el momento del `accept`. Funciona, pero es un puente, no un campo nativo del backend.

No declaro nada de esto como "100% verificado en producción" — lo que sí puedo afirmar con evidencia real adjunta arriba es: 51/51 pruebas de backend pasan, TypeScript compila limpio en SDK 57, y el flujo completo de sesión (crear → recomendar → aceptar → avanzar → pickup → delivery → finish) corrió de principio a fin contra el backend real en esta máquina.
