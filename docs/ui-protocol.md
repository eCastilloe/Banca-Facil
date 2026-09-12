# Protocolo de UI (A2UI) — v3, reconciliado con frontend

Reemplaza v1 (borrador plano, descartado) y v2 (envelope A2UI, pero con dos
endpoints separados). Este documento describe el contrato **real**, tomado
del esquema que frontend ya construyó (PR #6 — Sam + Jorge) y adaptado en
`backend/agent.py`. Ver CLAUDE.md sección 10 para el historial completo de
la reconciliación.

## Decisiones clave

- **Drill-down 100% local.** Cada categoría del desglose ya trae su lista
  completa de `transactions` anidada. El click en una porción/barra NO debe
  disparar ninguna llamada de red — el frontend solo alterna qué datos
  (ya recibidos) muestra. Esto extiende el tipo `CategoryBreakdownItem` del
  frontend, que hoy NO incluye `transactions` (ver "Pendiente en frontend"
  abajo — **todavía no aplicado**, al 2026-09-12).
- **Un solo endpoint con campo `event`** (`"overview"` | `"message"` |
  `"action"`), adoptando tal cual el contrato que implementó frontend en
  `frontend/A2UI-INTEGRATION.md` — no el diseño original de dos endpoints.
  `"action"` todavía no está soportado (responde 400) — alcance restringido
  a consulta + categorización por ahora. `POST /action` (ruta aparte,
  `crear_limite_gasto`) sigue existiendo para uso directo/futuro, pero no
  está conectado al `event`-dispatch del chat.
- **CORS habilitado** (`CORSMiddleware`, `allow_origins="*"` por default,
  configurable vía `CORS_ORIGINS`) — deliberado para la demo, sin datos
  sensibles reales; revisar si el proyecto sigue después del hackathon.
- **Nombres de campo en inglés**, tal como ya los espera el frontend. El
  contrato interno entre `agent.py` y el servidor MCP sigue en español (no
  cambia, ver CLAUDE.md sección 7) — la traducción pasa en `agent.py`.

## `POST /chat`

Request — tres variantes según `event`:

```json
// Al abrir la app, sin que el usuario haya escrito nada
{ "event": "overview", "conversation_id": "conv_123" }

// Pregunta en lenguaje natural
{ "event": "message", "message": "¿En qué gasté más este mes?", "conversation_id": "conv_123" }

// No soportado todavía -- responde 400
{ "event": "action", "component_id": "...", "action_id": "...", "params": {}, "conversation_id": "conv_123" }
```

`conversation_id` es opcional; si no se manda, el backend genera uno.
`event="overview"` salta la llamada a Gemini para resolver el periodo —
usa directo el mes actual (más rápido y barato que el caso más común, abrir
la app, dependa del LLM).

Response:

```json
{
  "version": "1.0",
  "intent": "entender_gastos",
  "conversation_id": "conv_123",
  "message": "Este mes tu mayor gasto fue en Compras, con $1,200.",
  "components": [
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
    }
  ]
}
```

### Campos

- **`type`**: `"pie_chart"` o `"bar_chart"` — coincide exactamente con las
  claves del `registry.tsx` del frontend. El agente decide cuál usar.
- **`message`**: texto breve del agente con el hallazgo principal. **No
  forma parte todavía del tipo `A2UIEnvelope` del frontend** (que hoy es
  `{version, intent, conversation_id, components}`) — se manda de una vez
  porque no rompe nada (TS/JS ignora campos extra), y queda disponible para
  cuando el frontend decida mostrarlo en algún lado (ej. arriba de la
  gráfica). No hay que bloquear nada esperando a que lo usen.
- **`categories[].transactions`**: `{id, date, description, amount}` por
  transacción. `amount` es **negativo** para gasto (mismo convenio que ya
  usa `TransactionList.tsx`).
- **`period.was_clamped`**: `true` si lo que pidió el usuario excedía el
  tope de 3 meses y se recortó. `requested_start`/`requested_end` guardan lo
  que el usuario pidió de verdad, sin recortar.
- Sin `actions` por ahora — no hay ninguna acción disparable desde el
  envelope de consulta todavía.

## Pendiente en frontend (no lo tocamos nosotros — avisar al equipo)

Para que el drill-down sea local de verdad, frontend necesita:

1. **`frontend/src/types/a2ui.ts`**: agregar `transactions: TransactionItem[]`
   a `CategoryBreakdownItem`.
2. **`PieChart.tsx` / `BarChart.tsx`**: cambiar `handleClick` para que, en
   vez de llamar `onAction(clickAction.id, {category_id})` (que hoy dispara
   `sendAction` → pensado para pegarle al backend), guarde la categoría
   seleccionada en estado local del componente y renderice inline los datos
   de `transactions` que ya vienen en `props` — sin ninguna llamada nueva.
   Pueden reutilizar `TransactionList.tsx` como sub-render pasándole props
   construidas en el cliente a partir de la categoría clickeada.
3. Como consecuencia, `view_category_detail`/`mockCategoryDetail` en
   `api.ts`/`mockAgent.ts` deja de ser necesario para este flujo (pueden
   limpiarlo o dejarlo sin usar, es su decisión).

## `POST /action` (ya implementado, no conectado al envelope aún)

```json
// Request
{ "accion": "crear_limite_gasto", "parametros": { "categoria": "Compras", "monto_limite": 960.0 } }

// Response
{ "ok": true, "limite": { "categoria": "Compras", "monto_limite": 960.0, "creado_en": "2026-09-12T18:30:00+00:00" } }
```

Nota: `categoria`/`monto_limite` aquí siguen en español porque hablan
directo con la tool MCP `crear_limite_gasto` (contrato interno, sin cambios).
Cuando se conecte a una acción disparada desde la UI, decidir ahí si el
`ComponentAction` correspondiente vive en español o inglés de cara al
frontend.
