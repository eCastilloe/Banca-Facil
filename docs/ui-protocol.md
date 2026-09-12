# Protocolo de UI (A2UI) — v4

Describe el contrato **real** entre `backend/agent.py` y el frontend. v4
agrega el router de intención y el ciclo cerrado por acciones; v3 asumía un
solo flujo (gastos) y acciones sin soportar. Ver CLAUDE.md secciones 10 y 11
para el historial y los contratos internos.

## Decisiones clave

- **La pantalla cambia según la intención.** Un router clasifica cada
  mensaje en `gasto_por_categoria`, `diagnostico_financiero`,
  `proximos_pagos` o `fuera_de_alcance`, y cada una compone su propio set
  de componentes. El `intent` del envelope dice cuál se resolvió.
- **El ciclo se cierra con `event:"action"`.** El agente ejecuta la acción
  vía MCP y responde con **otro envelope** (pantalla nueva), no con un
  `{ok:true}`. Es lo que cumple la regla 3 del reto.
- **Drill-down 100% local.** Cada categoría del desglose ya trae su lista
  completa de `transactions` anidada. El click en una porción/barra NO
  dispara ninguna llamada de red — el frontend solo alterna qué datos (ya
  recibidos) muestra. Excepción deliberada al ciclo, por robustez en el
  momento más visible de la demo.
- **Un solo endpoint con campo `event`** (`"overview"` | `"message"` |
  `"action"`), adoptando el contrato que implementó frontend en
  `frontend/A2UI-INTEGRATION.md`. `POST /action` **se eliminó**: quedaba
  superado por `event:"action"` y tener dos caminos para lo mismo solo
  confundía.
- **CORS habilitado** (`CORSMiddleware`, `allow_origins="*"` por default,
  configurable vía `CORS_ORIGINS`) — deliberado para la demo, sin datos
  sensibles reales; revisar si el proyecto sigue después del hackathon.
- **Nombres de campo en inglés**, tal como ya los espera el frontend. El
  contrato interno entre `agent.py` y el servidor MCP sigue en español —
  la traducción pasa en `agent.py`.

## `POST /chat`

Request — tres variantes según `event`:

```json
// Al abrir la app, sin que el usuario haya escrito nada
{ "event": "overview", "conversation_id": "conv_123" }

// Pregunta en lenguaje natural
{ "event": "message", "message": "¿En qué gasté más este mes?", "conversation_id": "conv_123" }

// El usuario pulsó algo de la UI generada -- responde una pantalla nueva
{ "event": "action", "component_id": "sugerencia_limite",
  "action_id": "crear_limite_gasto",
  "params": { "categoria": "Compras", "monto_limite": 3200 },
  "conversation_id": "conv_123" }
```

`conversation_id` es opcional; si no se manda, el backend genera uno.
`event="overview"` salta el router (ya sabemos la intención) y no gasta esa
llamada en el caso más común, abrir la app.

Todas las respuestas traen `suggested_prompts`: preguntas de seguimiento
que cambian según la pantalla mostrada. El frontend ya las renderiza en una
barra colapsable.

Response (ejemplo de `gasto_por_categoria`):

```json
{
  "version": "1.0",
  "intent": "gasto_por_categoria",
  "conversation_id": "conv_123",
  "suggested_prompts": ["¿Cómo voy este mes?", "¿Qué pagos tengo próximos?"],
  "components": [
    {
      "id": "insight",
      "type": "text_block",
      "props": { "title": "Compras se llevó el 35% de tu gasto." }
    },
    {
      "id": "spending_overview",
      "type": "pie_chart",
      "props": {
        "period": {
          "start": "2026-09-01",
          "end": "2026-09-30",
          "requested_start": "2026-09-01",
          "requested_end": "2026-09-30",
          "was_clamped": false
        },
        "total_spent": 3404.5,
        "categories": [
          {
            "id": "compras",
            "label": "Compras",
            "total": 1200.0,
            "percent": 35.2,
            "transactions": [
              { "id": "t8", "date": "2026-09-20", "description": "Liverpool", "amount": -1200.0 }
            ]
          }
        ]
      }
    },
    {
      "id": "sugerencia_limite",
      "type": "action_button",
      "props": {
        "label": "Crear límite de $960 en Compras",
        "action": "crear_limite_gasto",
        "params": { "categoria": "Compras", "monto_limite": 960 },
        "variant": "primary"
      }
    }
  ]
}
```

### Campos

- **`intent`**: qué resolvió el router — `gasto_por_categoria`,
  `diagnostico_financiero`, `proximos_pagos`, `fuera_de_alcance` o
  `limite_creado` (respuesta a una acción).
- **`type`** de la gráfica: `"pie_chart"` o `"bar_chart"` — coincide
  exactamente con las claves del registry del frontend. El agente decide.
- **`categories[].transactions`**: `{id, date, description, amount}` por
  transacción. `amount` es **negativo** para gasto (mismo convenio que ya
  usa `TransactionList.tsx`); los totales sí van positivos.
- **`period.was_clamped`**: `true` si lo que pidió el usuario excedía el
  tope de 3 meses y se recortó. `requested_start`/`requested_end` guardan lo
  que el usuario pidió de verdad, sin recortar.
- **`action_button`**: solo aparece cuando una categoría se lleva ≥30% del
  gasto. Los `params` van en español porque viajan tal cual a la tool MCP.
- **`suggested_prompts`**: siempre presente, cambia según la pantalla.

## El ciclo cerrado: `event:"action"`

El usuario pulsa el `action_button` → el frontend manda:

```json
{ "event": "action", "conversation_id": "conv_123",
  "component_id": "sugerencia_limite", "action_id": "crear_limite_gasto",
  "params": { "categoria": "Compras", "monto_limite": 960 } }
```

El agente ejecuta `crear_limite_gasto` vía MCP (escribe estado real en
disco) y responde con **una pantalla nueva**:

```json
{
  "version": "1.0",
  "intent": "limite_creado",
  "conversation_id": "conv_123",
  "suggested_prompts": ["¿Cómo voy este mes?", "¿En qué gasté más?"],
  "components": [
    { "id": "confirmacion", "type": "text_block",
      "props": { "title": "Listo, te aviso si Compras pasa de $960." } },
    { "id": "limite_progreso", "type": "progress",
      "props": { "label": "Compras este mes", "value": 1200, "max": 960 } }
  ]
}
```

Ese `progress` es lo que hace visible el ciclo: el límite que el usuario
acaba de crear ya se está midiendo contra su gasto real.

## Estado del drill-down local

Aplicado por frontend (`CategoryBreakdown.tsx` → `CategoryDetail.tsx`): el
click guarda la categoría en estado local y pinta sus `transactions` sin
red. El backend ya no manda acciones `category_click`, y cada categoría
incluye siempre su `transactions`.
Cuando se conecte a una acción disparada desde la UI, decidir ahí si el
`ComponentAction` correspondiente vive en español o inglés de cara al
frontend.
