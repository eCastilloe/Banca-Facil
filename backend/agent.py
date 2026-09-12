"""Agente del flujo de control de gasto por categoría.

Orquesta el flujo. Entrega en el esquema A2UI real ya construido 
por frontend

1. Gemini resuelve el periodo que pidió el usuario en lenguaje natural, SIN
   aplicarle el tope de 3 meses él mismo. Python aplica el tope de forma
   determinística después (no confiamos aritmética de fechas a la LLM).
2. Python llama a la tool MCP `obtener_gasto_por_categoria` con el rango ya
   acotado. El agente nunca clasifica ni agrega transacciones, esa lógica
   vive enteramente en el servidor MCP (contrato en español, interno).
3. Gemini decide el tipo de gráfica (pie_chart / bar_chart) y un mensaje
   breve, usando solo los totales por categoría (no la lista completa de
   transacciones, para no gastar tokens de más).
4. Python traduce la respuesta cruda de la tool (español, interno) al
   envelope A2UI que el frontend ya espera (inglés, con `transactions`
   anidadas por categoría) y lo regresa.

Decisión de equipo (2026-09-12): el drill-down de categoría es 100% local
en el frontend -- por eso cada categoría ya trae su `transactions` completa
desde esta respuesta, y el envelope NO incluye ninguna acción de tipo
"category_click". El endpoint de acciones (`POST /action`,
`crear_limite_gasto`) existe y funciona, pero todavía no está conectado al
envelope del chat -- eso queda para una siguiente iteración ("restringir a
solo consulta y categorización por ahora", ver CLAUDE.md sección 8).

Decisión de equipo (2026-09-12, reconciliación #2): `/chat` adopta el
contrato de un solo endpoint + campo `event` que ya construyó e implementó
frontend (`frontend/A2UI-INTEGRATION.md`) -- `"overview"` (sin mensaje, al
abrir la app), `"message"` (pregunta en lenguaje natural), o `"action"`
(no soportado aún, ver párrafo anterior). No hay pérdida de capacidad real
frente al diseño de dos endpoints de CLAUDE.md sección 5 -- es la misma
información, solo que en el body en vez de en la ruta.

Nota de diseño: esto usa function calling manual (Python llama la tool MCP
directamente) en vez del soporte "automático" experimental de Gemini para
sesiones MCP. Se eligió así por confiabilidad para la demo en vivo -- el
modo automático depende de comportamiento interno de la SDK que hoy no
está bien documentado. Migrar a modo automático más adelante no debería
requerir tocar el servidor MCP.

Nota técnica: el cliente MCP usado aquí es el SDK oficial (`mcp.client.stdio`
+ `ClientSession`), no el paquete de terceros `fastmcp` (su client arrastra
una versión de `mcp` incompatible con el `FastMCP` ya elegido para el
servidor -- ver requirements.txt).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

load_dotenv()

BACKEND_DIR = Path(__file__).parent
MODEL = "gemini-3.6-flash"  # ajustar si el equipo decide otro modelo

TOPE_MESES = 3

# Traduce el nombre de categoría interno (español, del contrato MCP) al
# id/label que el frontend ya espera (frontend/src/lib/categoryColors.ts
# fija los colores por este mismo id -- mantenerlos sincronizados).
CATEGORIA_INFO = {
    "Despensa": {"id": "despensa", "label": "Despensa"},
    "Comidas/Restaurantes": {"id": "comida", "label": "Comida y restaurantes"},
    "Servicios": {"id": "servicios", "label": "Servicios"},
    "Transporte": {"id": "transporte", "label": "Transporte"},
    "Entretenimiento/Suscripciones": {"id": "entretenimiento", "label": "Entretenimiento y suscripciones"},
    "Salud": {"id": "salud", "label": "Salud"},
    "Compras": {"id": "compras", "label": "Compras"},
    "Otros": {"id": "otros", "label": "Otros / sin categorizar"},
}

app = FastAPI(title="Control de Gasto por Categoría")

# Frontend (Vite) y backend corren en orígenes distintos -- sin esto el
# navegador bloquea el fetch aunque el backend responda bien. "*" es
# deliberado para la demo (sin datos sensibles reales, todo sintético);
# para algo más allá del hackathon, restringir vía CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def _llamar_tool_mcp(nombre: str, argumentos: dict[str, Any]) -> Any:
    # -m mcp_server.server (no la ruta del archivo): server.py usa imports
    # relativos hacia el Bloque 1 (`from . import classification, data`),
    # así que necesita correr como módulo del paquete `mcp_server`, con
    # `backend/` como cwd, para que esos imports no truenen.
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(BACKEND_DIR),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resultado = await session.call_tool(nombre, argumentos)
    if resultado.isError:
        detalle = resultado.content[0].text if resultado.content else "Error desconocido en tool MCP"
        raise RuntimeError(detalle)
    return json.loads(resultado.content[0].text)


class ChatRequest(BaseModel):
    event: str = "message"  # "overview" | "message" | "action" (ver A2UI-INTEGRATION.md de frontend)
    message: str | None = None
    conversation_id: str | None = None
    component_id: str | None = None
    action_id: str | None = None
    params: dict[str, Any] | None = None


class ActionRequest(BaseModel):
    accion: str
    parametros: dict[str, Any]


# --- Paso 1: resolver el periodo (sin tope -- el tope lo aplica Python) -----

PERIODO_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "fecha_inicio": types.Schema(type=types.Type.STRING, description="YYYY-MM-DD"),
        "fecha_fin": types.Schema(type=types.Type.STRING, description="YYYY-MM-DD"),
    },
    required=["fecha_inicio", "fecha_fin"],
)


async def _resolver_periodo_solicitado(mensaje_usuario: str) -> tuple[date, date]:
    hoy = date.today()
    prompt = f"""Hoy es {hoy.isoformat()}.

El usuario preguntó: "{mensaje_usuario}"

Interpreta a qué rango de fechas se refiere (ej. "el mes pasado",
"últimos 2 meses") y responde con fecha_inicio y fecha_fin en formato
YYYY-MM-DD. Si el usuario no especifica ninguna fecha, usa el mes actual
completo. No te preocupes por ningún límite máximo de rango -- eso se
aplica después."""

    response = await gemini_client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PERIODO_SCHEMA,
        ),
    )
    datos = json.loads(response.text)
    return date.fromisoformat(datos["fecha_inicio"]), date.fromisoformat(datos["fecha_fin"])


def _aplicar_tope(solicitado_inicio: date, solicitado_fin: date) -> tuple[date, date, bool]:
    tope_minimo = date.today() - timedelta(days=TOPE_MESES * 31)
    inicio_real = max(solicitado_inicio, tope_minimo)
    fue_recortado = inicio_real != solicitado_inicio
    return inicio_real, solicitado_fin, fue_recortado


# --- Paso 3: decidir tipo de gráfica + mensaje ------------------------------

DECISION_UI_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "variante": types.Schema(type=types.Type.STRING, enum=["pie_chart", "bar_chart"]),
        "mensaje": types.Schema(type=types.Type.STRING),
    },
    required=["variante", "mensaje"],
)


async def _decidir_ui(categorias: list[dict]) -> dict:
    resumen = [{"label": c["label"], "total": c["total"], "percent": c["percent"]} for c in categorias]
    prompt = f"""Este es el desglose de gasto por categoría del periodo consultado:

{json.dumps(resumen, ensure_ascii=False)}

Decide:
- "variante": "pie_chart" si 1-2 categorías dominan claramente el gasto,
  "bar_chart" si los montos están más parejos.
- "mensaje": una frase breve (en español) describiendo el hallazgo
  principal para mostrarle al usuario."""

    response = await gemini_client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DECISION_UI_SCHEMA,
        ),
    )
    return json.loads(response.text)


# --- Orquestación ------------------------------------------------------------


def _traducir_categorias(gasto_por_categoria: dict[str, dict], total_spent: float) -> list[dict]:
    categorias = []
    contador_tx = 0
    for categoria_es, datos in gasto_por_categoria.items():
        info = CATEGORIA_INFO.get(
            categoria_es,
            {"id": categoria_es.lower().replace("/", "_").replace(" ", "_"), "label": categoria_es},
        )
        transactions = []
        for t in datos["transacciones"]:
            contador_tx += 1
            transactions.append(
                {
                    "id": f"t{contador_tx}",
                    "date": t["fecha"],
                    "description": t["comercio"],
                    "amount": -t["monto"],  # frontend usa montos negativos para gasto
                }
            )
        percent = round((datos["monto_total"] / total_spent * 100), 1) if total_spent else 0.0
        categorias.append(
            {
                "id": info["id"],
                "label": info["label"],
                "total": datos["monto_total"],
                "percent": percent,
                "transactions": transactions,
            }
        )
    return categorias


async def _llamar_agente(mensaje_usuario: str | None, conversation_id: str) -> dict:
    if mensaje_usuario:
        solicitado_inicio, solicitado_fin = await _resolver_periodo_solicitado(mensaje_usuario)
    else:
        # event="overview" (o mensaje vacío): default directo a mes actual,
        # sin gastar una llamada a Gemini en el caso más común (abrir la app).
        hoy = date.today()
        solicitado_inicio, solicitado_fin = hoy.replace(day=1), hoy

    fecha_inicio, fecha_fin, fue_recortado = _aplicar_tope(solicitado_inicio, solicitado_fin)

    gasto_por_categoria = await _llamar_tool_mcp(
        "obtener_gasto_por_categoria",
        {"fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()},
    )

    period = {
        "start": fecha_inicio.isoformat(),
        "end": fecha_fin.isoformat(),
        "requested_start": solicitado_inicio.isoformat(),
        "requested_end": solicitado_fin.isoformat(),
        "was_clamped": fue_recortado,
    }

    if not gasto_por_categoria:
        # components=[] -- el frontend ya tiene su propio estado vacío
        # ("No hay resultados para esta consulta" + botón volver al resumen),
        # más consistente que armar un text_block propio para este caso.
        return {
            "version": "1.0",
            "intent": "entender_gastos",
            "conversation_id": conversation_id,
            "components": [],
        }

    total_spent = sum(datos["monto_total"] for datos in gasto_por_categoria.values())
    categorias = _traducir_categorias(gasto_por_categoria, total_spent)

    decision = await _decidir_ui(categorias)

    return {
        "version": "1.0",
        "intent": "entender_gastos",
        "conversation_id": conversation_id,
        "components": [
            {
                "id": "insight",
                "type": "text_block",
                "props": {"title": decision["mensaje"]},
            },
            {
                "id": "spending_overview",
                "type": decision["variante"],
                "props": {
                    "period": period,
                    "total_spent": total_spent,
                    "categories": categorias,
                },
            },
        ],
    }


# --- Endpoints HTTP (consumidos únicamente por el frontend) ----------------


@app.post("/chat")
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    if req.event == "action":
        raise HTTPException(
            status_code=400,
            detail="Acciones no soportadas en /chat todavía -- alcance restringido a consulta y categorización.",
        )
    try:
        return await _llamar_agente(req.message, conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/action")
async def action(req: ActionRequest):
    if req.accion != "crear_limite_gasto":
        raise HTTPException(status_code=400, detail=f"Acción no soportada: {req.accion}")
    try:
        return await _llamar_tool_mcp("crear_limite_gasto", req.parametros)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
