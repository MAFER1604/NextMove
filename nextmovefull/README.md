# NextMove — Demo de Infosys Hackathon

NextMove ayuda a alguien que ya tiene un trayecto planeado (p. ej. ir de su
casa al Tec de Monterrey antes de cierta hora) a aceptar pedidos de delivery
en el camino, sin poner en riesgo su llegada. Este repo es un **demo de
hackathon**: estable, evaluable, reproducible y explicable — no una app
comercial.

> ⚠️ **Aviso importante sobre el contrato oficial.** El contrato oficial de
> Infosys (`backend/contracts/`) define un optimizador de turno de repartidor
> genérico por **zonas** (no coordenadas GPS), sin un campo de "destino
> personal obligatorio". Siguiendo la regla de que el contrato oficial
> prevalece, mapeamos así (sin inventar campos oficiales):
> - `shift_end_time` = la hora límite para llegar al destino final del usuario.
> - Un campo **interno** (no oficial) `final_destination_zone` en
>   `domain_models.ShiftConfig` representa ese destino.
> - Los baselines oficiales son los del CSV (`AcceptAll`, `HighestPay`,
>   `NearestFirst`, `GreedyRate`) + `OurAgent` (NextMove) + `Oracle`.

---

## 1. Arquitectura

```
nextmove/
├── backend/          FastAPI + Pydantic, Python 3.11+
│   ├── contracts/     Archivos OFICIALES de Infosys, sin modificar
│   ├── constraints/    Las 5 restricciones de seguridad, una clase cada una
│   ├── baselines/      AcceptAll, HighestPay, NearestFirst, GreedyRate, Oracle
│   ├── config/         Límites de seguridad, perfiles de vehículo, config de sim
│   ├── data/            Ubicaciones, demanda, semillas dev/eval, demo fijo
│   ├── outputs/          event_logs/, decision_logs/, results/ (generados)
│   ├── tests/            31 pruebas automatizadas (pytest)
│   ├── models.py         Contrato OFICIAL (DecideRequest/DecideResponse)
│   ├── domain_models.py  Modelos INTERNOS (separados del contrato)
│   ├── decide.py         Adaptador oficial de POST /decide (fast path, <50ms)
│   ├── decision_engine.py Motor NextMove (seguridad → ruta → tiempo → economía)
│   ├── scenario_generator.py Generador determinista por semilla
│   ├── simulation_engine.py  Multi-agente sobre el mismo stream de eventos
│   ├── replay_engine.py      Replay determinista + diff
│   ├── evaluation.py         Corre semillas held-out, llena el CSV oficial
│   ├── strategy_provider.py  Integración opcional Claude/Ollama (fuera del fast path)
│   └── main.py                FastAPI app con todos los endpoints
└── mobile/            Expo + React Native + TypeScript
    ├── App.tsx           Pantalla principal
    ├── components/        SetupPanel, SimulationControls, AgentPanel, RouteMap,
    │                       EventBanner, DecisionCard, DecisionLogModal,
    │                       ResultsPanel, EvaluationPanel, ReplayPanel
    ├── hooks/useSimulation.ts  Polling, ticks, sin llamadas superpuestas
    └── services/api.ts    Único punto de contacto con el backend
```

**Separación de modelos** (sección 5 del brief): `models.py` (oficial) y
`domain_models.py` (interno) están deliberadamente separados, con `decide.py`
como capa de adaptación. Esto permite que el contrato oficial cambie sin
reescribir el motor.

---

## 2. Requisitos

- Python 3.11+ (probado con 3.12)
- Node.js 18+ y npm (probado con Node 22)
- Expo CLI (se instala vía `npx`, no hace falta instalar global)
- Un teléfono con la app **Expo Go**, o un emulador/simulador, para probar el frontend

---

## 3. Backend: instalación y ejecución

### macOS/Linux
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # opcional: no se necesita ninguna clave para correr el demo
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Windows PowerShell
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Verifica que está vivo:
```bash
curl http://localhost:8000/health
```

Documentación interactiva (Swagger) en `http://localhost:8000/docs`.

---

## 4. Frontend: instalación y ejecución

```bash
cd mobile
npm install
cp .env.example .env
# edita .env con la URL correcta (ver sección 5)
npx expo start
```

### Uso desde teléfono físico
1. Averigua la IP LAN de tu computadora (`ipconfig` en Windows, `ifconfig`/`ip a` en macOS/Linux).
2. En `mobile/.env`: `EXPO_PUBLIC_API_URL=http://<tu-ip-lan>:8000`
3. Asegúrate de que el teléfono y la computadora estén en la misma red Wi-Fi.
4. Corre `npx expo start` y escanea el código QR con la app **Expo Go**.

### Emulador Android
`EXPO_PUBLIC_API_URL=http://10.0.2.2:8000` (localhost del host no es accesible directo desde el emulador).

### Simulador iOS / Expo Web
`EXPO_PUBLIC_API_URL=http://localhost:8000` funciona directo.

**Nota de diseño:** el mapa (`RouteMap.tsx`) es un mapa **esquemático
determinista** (zonas en una grilla fija), no `react-native-maps`. Se decidió
así a propósito para evitar una dependencia nativa frágil en Expo Go —
sigue mostrando con claridad origen, destino, zonas bloqueadas y la posición
de ambos agentes, que es lo que el demo necesita.

---

## 5. Ejecutar el demo fijo (guion de presentación)

Semilla fija: **777**, 3 horas de turno, moto, de Centro (zona 1) al Tec de
Monterrey (zona 7) — definida en `backend/data/fixed_demo.json`.

En el frontend: Setup → escenario **"Demo fijo"** → Generate & Start.

Con esta semilla (verificado en este demo, corrida real):
- **20 pedidos ofrecidos**, con eventos: 1 surge, 1 cierre vial, 1 retraso de
  restaurante de 15 min.
- NextMove activa **2 restricciones oficiales distintas**: `vehicle_capacity`
  (pedido "trampa" de pago alto con exceso de peso) y `shift_end_infeasible`
  (pedidos tardíos que pondrían en riesgo la llegada).
- Fallo de modelo: botón "⚠️ Simulate failure" en los controles → el badge
  cambia a "Modelo degradado" y NextMove sigue decidiendo con la última
  estrategia conocida, sin detenerse ni exceder el presupuesto de 50ms.
- Al terminar: `Replay shift` → `Replay match: PASS`.

Resultado real de esta corrida (ver sección 8 para más semillas):
| Agente | Completados | Ganancia neta | Violaciones |
|---|---|---|---|
| NextMove | 8 | $464.68 MXN | 0 |
| HighestPay | 9 | $507.29 MXN | 0 |
| NearestFirst | 11 | $538.01 MXN | 0 |
| GreedyRate | 4 | $250.72 MXN | 0 |
| AcceptAll | 11 | $509.04 MXN | 0 |
| Oracle | 11 | $509.04 MXN | 0 |

En este turno corto (3h), los baselines "ingenuos" completan más pedidos en
términos brutos; la ventaja real de NextMove se ve en turnos completos de 8h
sobre semillas held-out (sección 8) y en que **duplica la ganancia de
GreedyRate** (el baseline más parecido, sin demanda futura ni batching),
demostrando el valor del lookahead.

---

## 6. Ejecutar evaluación (semillas held-out)

```bash
curl -X POST http://localhost:8000/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"seed_set": "evaluation", "shift_hours": 8.0, "vehicle": "moto", "start_location_zone": 1, "final_destination_zone": 7}'
```

O desde el frontend: botón **"Run unseen evaluation"**.

Semillas de desarrollo (`backend/data/development_seeds.json`, usadas para
ajustar): `[1, 2, 3, 4, 5, 6, 7, 8]`
Semillas de evaluación (`backend/data/evaluation_seeds.json`, held-out,
**disjuntas**): `[101, 102, 103, 104, 105, 106, 107, 108, 109, 110]`

El CSV se escribe en `backend/outputs/results/results_evaluation.csv` con los
encabezados oficiales sin modificar.

---

## 7. Ejecutar replay

```bash
curl -X POST http://localhost:8000/replay \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<el que te devolvió /scenario/generate>", "agent": "NextMove"}'
```

Devuelve `{"match": true, ...}` o `{"match": false, "first_difference": {...}}`.

---

## 8. Resultados reales (no inventados)

### Pruebas automatizadas
```
cd backend && python3 -m pytest tests/ -v
```
**31 passed, 0 failed** (última corrida real). Cobertura: formato,
`/decide`, latencia, determinismo, las 5 restricciones (cada una activada al
menos una vez), replay, baselines, fallo de modelo.

### Latencia de `/decide` (1000 llamadas, medidas con `time.perf_counter`)
| Métrica | Valor medido |
|---|---|
| Promedio | ~0.03 ms |
| p95 | ~0.05 ms |
| Máximo | ~0.13 ms |
| Presupuesto | 50 ms |

(El *round trip* HTTP completo medido por `validate_format.py --endpoint`,
que incluye overhead de red/proceso del servidor de desarrollo, fue de
~40ms — todavía dentro del presupuesto, pero ese número no es el tiempo de
decisión puro, que es el de la tabla de arriba).

### Validador oficial
```
python3 contracts/validate_format.py --event-log outputs/event_logs/<id>.jsonl
python3 contracts/validate_format.py --endpoint http://localhost:8000/decide
```
Ambos: **PASS** (corrida real, ver logs de esta sesión de desarrollo).

### Evaluación sobre las 10 semillas held-out (8h, moto, zona 1→7)
| Policy | mean_earnings_mxn | mean_mxn_per_hr | orders_completed | deadline_misses | safety_violations |
|---|---|---|---|---|---|
| AcceptAll | 670.03 | 83.75 | 13.2 | 0 | 0 |
| HighestPay | 756.68 | 94.59 | 13.2 | 0 | 0 |
| NearestFirst | 666.52 | 83.32 | 13.0 | 0 | 0 |
| GreedyRate | 798.65 | 99.83 | 11.5 | 0 | 0 |
| **OurAgent (NextMove)** | **803.13** | **100.39** | 12.9 | 0 | 0 |
| Oracle | 670.03 | 83.75 | 13.2 | 0 | 0 |

**NextMove obtiene la mayor ganancia media y la mayor ganancia por hora de
todos los agentes** en las semillas held-out, con cero violaciones de
seguridad y cero incumplimientos de hora límite. `deadline_misses` es
estructuralmente 0 para todos: `shift_end_infeasible` es una restricción
dura que nunca deja aceptar un pedido infactible, así que nunca se llega
tarde por haber aceptado de más.

---

## 9. Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Las 5 restricciones de seguridad | `backend/constraints/*.py` (una por archivo) |
| Límites numéricos (centralizados) | `backend/config/safety_limits.py` |
| Perfiles de vehículo | `backend/config/vehicle_profiles.json` |
| Event logs generados | `backend/outputs/event_logs/*.jsonl` |
| Resultados de evaluación (CSV) | `backend/outputs/results/*.csv` |
| Cómo simular fallo del modelo | `POST /model/simulate-failure` y `/model/recover`, o botones en el frontend |
| Historial de decisiones | `GET /decisions` y `GET /decisions/{order_id}` (explain_decision) |

---

## 10. Estado de cumplimiento de los criterios de aceptación

| Criterio | Estado |
|---|---|
| Backend y frontend arrancan | ✅ Backend probado extensamente; frontend compila TypeScript sin errores (no se pudo correr Expo Go real en este entorno sandbox sin dispositivo) |
| `/decide` respeta el esquema oficial | ✅ `validate_format.py --endpoint` PASS |
| Event log respeta el esquema | ✅ `validate_format.py --event-log` PASS |
| Decisión no llama servicios externos | ✅ Sin imports de red en `decide.py`/`decision_engine.py` |
| Presupuesto de 50ms | ✅ avg 0.03ms, p95 0.05ms, max 0.13ms (medido, 1000 corridas) |
| Misma semilla ⇒ mismo flujo byte a byte | ✅ probado (`test_determinism.py`) |
| Replay produce decisiones idénticas | ✅ `test_replay.py`, corregido un bug real de orden de tick |
| Las 5 restricciones existen en código | ✅ `backend/constraints/` |
| ≥2 restricciones activadas en el demo | ✅ `vehicle_capacity` y `shift_end_infeasible`, semilla 777 |
| Razones <40 palabras | ✅ `test_reason_is_under_40_words` |
| `binding_constraint` correcto | ✅ distingue seguridad vs económico (`test_safety_refusal_distinguishable_from_economic_refusal`) |
| Modelo puede fallar sin detener el fast path | ✅ `test_model_failure.py` |
| Agentes reciben los mismos eventos | ✅ `test_all_agents_receive_identical_order_stream` |
| Baselines con nombre | ✅ 4 baselines del CSV oficial + Oracle |
| Semillas dev/eval separadas | ✅ archivos disjuntos |
| Explicar decisión en <10s | ✅ `GET /decisions/{order_id}`, no recalcula, lee el log |
| No hay resultados inventados | ✅ todos los números de este README son de corridas reales durante el desarrollo |
| Funciona sin TomTom/Claude/Ollama | ✅ `MockRouteProvider` + `StrategyProvider` sin credenciales, por defecto |

---

## 11. Limitaciones declaradas del demo

- **Oracle es una aproximación, no un solver ILP/DP exacto.** Acepta
  cualquier pedido seguro con ganancia neta ≥ 0 (piso 0 MXN/hr). En las
  semillas probadas coincide numéricamente con `AcceptAll` porque, dado el
  generador actual, casi todos los pedidos seguros tienen ganancia neta no
  negativa. Un oráculo verdadero requeriría programación dinámica/ILP sobre
  el flujo completo de pedidos, fuera de alcance de este demo.
- **`deadhead_pct_of_km`** no se trackea por separado del resto de la
  distancia recorrida; se reporta como `n/a` en el CSV en vez de inventar un
  número.
- **El mapa es esquemático**, no usa `react-native-maps` ni coordenadas GPS
  reales (ver sección 4).
- **El StrategyProvider no hace llamadas reales a Claude/Ollama**: el punto
  de extensión está documentado y aislado (`strategy_provider.py`), pero
  implementar la llamada real de red queda fuera del alcance de este demo
  (el prompt es explícito en que el modelo nunca debe estar en el fast path,
  así que su ausencia no afecta ningún criterio de aceptación).
- **El frontend no se probó en un dispositivo físico ni en Expo Go real**
  dentro de este entorno (sin acceso a un teléfono/emulador). Se verificó
  que TypeScript compila sin errores (`npx tsc --noEmit`) y que la lógica de
  API/estado sigue el contrato de endpoints del backend, pero recomiendo
  correr `npx expo start` y probarlo en un dispositivo antes de la
  presentación.
- **`current_zone`/rutas usan un modelo de distancia entre zonas simplificado**
  (no un grafo real de calles), consistente con que el contrato oficial
  tampoco expone coordenadas.

## 12. Guion breve para la demo en vivo

1. Setup → Demo fijo (semilla 777) → Generate & Start.
2. Deja correr ~30s: aparece el primer ACCEPT rentable de NextMove.
3. Cuando salga el pedido de "peso alto" → verás SKIP con
   `vehicle_capacity` en rojo (restricción de seguridad).
4. Banner de surge → sigue corriendo.
5. Banner de cierre vial → NextMove replanea automáticamente.
6. Banner de retraso de restaurante (+15 min).
7. Pulsa **"⚠️ Simulate failure"** → badge pasa a "Modelo degradado";
   NextMove sigue decidiendo (fast path no depende del modelo).
8. Al terminar el turno → panel de resultados, comparación NextMove vs
   HighestPay.
9. **Replay shift** → `Replay match: PASS`.
10. **Run unseen evaluation** → tabla contra los 6 baselines/oráculo.
