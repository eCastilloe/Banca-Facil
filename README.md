# Control de Gasto por Categoría — HackMTY 2026, Track Banorte

Un asistente financiero conversacional: la persona escribe en una sola caja
de texto y un agente (LLM) decide **qué intención es** y **qué pantalla
armar** — nunca solo texto plano. El agente trae los datos vía un servidor
MCP (nunca los toca directamente) y responde con una interfaz descrita en
un protocolo propio tipo A2UI. Cada interacción con esa interfaz (por
ejemplo, crear un límite de gasto) regresa al agente y produce una pantalla
nueva, cerrando el ciclo que exige el reto.

Documentación más a fondo:

- [`docs/arquitectura.md`](docs/arquitectura.md) — diagrama de flujo,
  decisiones técnicas y sus trade-offs.
- [`docs/ui-protocol.md`](docs/ui-protocol.md) — el esquema A2UI (envelope,
  catálogo de componentes, contrato de `POST /chat`).
- [`frontend/A2UI-INTEGRATION.md`](frontend/A2UI-INTEGRATION.md) — cómo
  probar el frontend en modo mock y cómo conectarlo al backend real.

## Qué hace hoy

Cuatro intenciones, cada una con su propia pantalla (ver
`docs/ui-protocol.md`):

| Intención | Pregunta de ejemplo | Componentes que arma |
|---|---|---|
| `gasto_por_categoria` | "¿en qué gasté de más este mes?" | `text_block` + `pie_chart`/`bar_chart`/`table` + `action_button` (sugerencia de límite) |
| `diagnostico_financiero` | "¿cómo voy este mes?" | `text_block` + `risk_indicator` + `category_badge` + `progress` + `action_button` (quitar límite, si existe) |
| `proximos_pagos` | "¿qué pagos tengo próximos?" | `text_block` + `transaction_list` (cargos recurrentes proyectados) |
| `fuera_de_alcance` | "cuéntame un chiste" | `text_block` + `suggested_prompts` |

La variante de `gasto_por_categoria` la decide Gemini con un criterio
numérico explícito (no "a juicio libre" del modelo): pastel si una
categoría domina (≥45% del total, o dobla a la segunda), tabla si hay 4+
categorías parejas entre sí (ninguna le saca más de 15 puntos a la
siguiente — ahí ni pastel ni barras dejan comparar montos con precisión),
barras en cualquier otro caso.

Además, si el gasto de una categoría ya supera un límite guardado, la
respuesta lo antepone como aviso (`risk_indicator`) desde la primera
pantalla que se vea — al abrir la app o al preguntar por el gasto, no solo
si se pregunta "¿cómo voy?" con esas palabras.

Y el ciclo de acción que cierra la regla 3 del reto, ahora completo en las
dos direcciones: el usuario pulsa "Crear límite de $X en Categoría" → el
agente ejecuta `crear_limite_gasto` vía MCP (modifica estado guardado de
verdad) → responde con una pantalla nueva confirmando el límite, ya medido
contra el gasto real. Desde el diagnóstico, también se puede "Quitar
límite" (`eliminar_limite_gasto`) — crear, ver el efecto, y ajustar o
quitar es el mismo ciclo.

Las cuatro intenciones y las dos acciones están conectadas de punta a punta
contra el Bloque 1 real (sin mocks) y probadas con Gemini real.

## Estructura del repo

```
backend/
  agent.py                       # FastAPI (POST /chat): router de intención,
                                  # handlers, cliente Gemini + cliente MCP
  mcp_server/
    server.py                    # FastMCP: registra las tools sobre el Bloque 1
    data.py                      # transacciones sintéticas + límites guardados
    classification.py            # diccionario + caché + fallback LLM + "Otros" +
                                  # diagnóstico financiero + próximos pagos
    categorias.py                # las 8 categorías válidas + tipos de movimiento excluidos
  tests/                         # pytest — corre sin FastMCP ni Gemini de por medio
frontend/
  src/
    App.tsx                      # pantalla única, reemplaza su contenido con cada respuesta
    components/
      registry.tsx               # punto de entrada: resuelve `type` -> componente React
      a2ui/                      # catálogo A2UI validado (pie_chart, bar_chart, progress,
                                  # category_badge, action_button, risk_indicator, text_block)
      TransactionList.tsx        # el único componente fuera de a2ui/
    lib/
      api.ts                     # fetch real o mock, timeout + mensajes de error
      parseEnvelope.ts           # valida el envelope en la frontera (mock y HTTP por igual)
      mockAgent.ts                # respuestas de ejemplo para correr sin backend
  A2UI-INTEGRATION.md
docs/
  arquitectura.md
  ui-protocol.md
```

## Requisitos

- Python 3.11+
- Node 20+
- Una o más API keys de [Gemini](https://aistudio.google.com/) (capa
  gratuita: 20 solicitudes/día por key — ver nota de cuota abajo). Sin
  ellas el backend no arranca, pero el frontend sí funciona solo (modo mock).

## Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# editar .env y poner GEMINI_API_KEYS=tu_key_1,tu_key_2,...

uvicorn agent:app --reload --port 8000
```

`agent.py` levanta el servidor MCP (`server.py`) internamente como
subproceso (`python -m mcp_server.server`) — no hay que correrlo aparte.

Variables de entorno (`backend/.env.example`):

- `GEMINI_API_KEYS` (o `GEMINI_API_KEY` en singular) — una o varias keys
  separadas por coma; el agente rota a la siguiente si una responde 429.
- `CORS_ORIGINS` (opcional) — orígenes permitidos separados por coma. Sin
  definir, se permite cualquiera (suficiente para demo local).

Tests (Bloque 1 completo: datos, clasificación, diagnóstico financiero y
próximos pagos — lógica pura, sin FastMCP ni Gemini de por medio):

```bash
cd backend
pytest -q
# 62 passed
```

### Nota de cuota de Gemini

La capa gratis da 20 solicitudes/día por key, y cada consulta del usuario
cuesta 2 llamadas (router de intención + decisión de UI). `GEMINI_API_KEYS`
acepta varias separadas por coma — el agente rota a la siguiente
automáticamente si una responde 429 (cuota agotada).

## Frontend

```bash
cd frontend
npm install
npm run dev
# abre http://localhost:5173/
```

**Funciona sin backend por default** (modo mock, con datos de ejemplo) —
útil para desarrollar la UI sin depender de Gemini ni de la cuota. Para
conectarlo al backend real:

```bash
cp .env.example .env.local
# editar .env.local:
#   VITE_A2UI_ENDPOINT=http://localhost:8000/chat
```

reinicia `npm run dev` después de editar. Variables de entorno
(`frontend/.env.example`):

- `VITE_A2UI_ENDPOINT` — vacío usa el mock; con una URL, habla por HTTP
  con el agente real y muestra sus errores tal cual (sin sustituirlos por
  datos ficticios).
- `VITE_A2UI_TIMEOUT_MS` (opcional) — milisegundos antes de cancelar una
  consulta; default 15000 si se deja vacío o no es un número válido.

Verificación:

```bash
npm run build   # tsc -b && vite build
npm run lint    # oxlint
node --experimental-strip-types --test tests/a2ui.test.mjs
```

## Protocolo de UI (A2UI)

El agente responde con un envelope `{version, intent, conversation_id,
components, suggested_prompts}`. Catálogo cerrado de componentes — agregar
uno nuevo es registrar un `type` más, no cambiar el contrato:

`text_block`, `pie_chart`, `bar_chart`, `transaction_list`, `progress`,
`risk_indicator`, `category_badge`, `action_button`.

El drill-down de categoría (ver una porción/barra) es **100% local**: cada
categoría ya trae su lista completa de transacciones anidada, así que el
click no dispara ninguna llamada de red. El detalle completo (campos,
ejemplos de request/response, el ciclo de `event:"action"`) está en
[`docs/ui-protocol.md`](docs/ui-protocol.md).

## Datos

Las transacciones son **sintéticas**, generadas por el propio equipo y
declaradas como tales (no hay acceso a una API real de Banorte ni a un
proveedor de Open Finance). Se generan de forma determinista por fecha, así
que la ventana móvil de 3 meses hacia atrás nunca queda obsoleta y no
requiere persistirse a disco. Los límites de gasto que la persona crea sí
se persisten (JSON en disco), porque son estado real. Ver
[`docs/arquitectura.md`](docs/arquitectura.md#capa-de-datos-aislada-y-reemplazable)
para el detalle de por qué esta capa está aislada y es reemplazable por una
fuente real sin tocar el resto del sistema.
