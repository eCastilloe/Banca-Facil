# Control de Gasto por Categoría — HackMTY 2026, Track Banorte

Un asistente financiero conversacional: la persona escribe en una sola caja
de texto ("¿en qué gasté de más este mes?", "¿cómo voy?", "¿qué pagos tengo
próximos?") y un agente (LLM) decide qué intención es, trae los datos vía un
servidor MCP, y responde con una interfaz generada dinámicamente (protocolo
propio tipo A2UI) — nunca solo texto plano. Cada interacción con esa
interfaz (por ejemplo, crear un límite de gasto) regresa al agente y
produce una pantalla nueva, cerrando el ciclo que pide el reto.

Documentación más a fondo:

- [`docs/arquitectura.md`](docs/arquitectura.md) — diagrama de flujo,
  decisiones técnicas y sus trade-offs.
- [`docs/ui-protocol.md`](docs/ui-protocol.md) — el esquema A2UI (envelope,
  catálogo de componentes).

## Estructura del repo

```
backend/
  agent.py                # FastAPI (POST /chat): cliente Gemini + cliente MCP
  mcp_server/
    server.py             # FastMCP: registra las tools sobre el Bloque 1
    data.py                # transacciones sintéticas + límites de gasto guardados
    classification.py      # diccionario + caché + fallback LLM + "Otros"
    categorias.py           # las 8 categorías válidas + tipos de movimiento excluidos
  tests/                   # pytest, corre sin FastMCP ni Gemini de por medio
frontend/                  # React + Vite + TypeScript, catálogo de componentes A2UI
docs/
  arquitectura.md
  ui-protocol.md
```

## Requisitos

- Python 3.11+
- Node 20+
- Una o más API keys de [Gemini](https://aistudio.google.com/) (capa
  gratuita: 20 solicitudes/día por key — ver nota de cuota abajo)

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

Para correr los tests del Bloque 1 (datos + clasificación, sin red ni
Gemini de por medio):

```bash
cd backend
pytest -q
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
cp .env.example .env.local
# editar .env.local:
#   VITE_A2UI_ENDPOINT=http://localhost:8000/chat

npm run dev
# abre http://localhost:5173/
```

Si `VITE_A2UI_ENDPOINT` se deja vacío, el frontend usa datos de ejemplo
locales sin necesidad de levantar el backend.

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
