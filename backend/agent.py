"""Agente: interpreta la intención y arma la pantalla que le corresponde.

Un solo endpoint (`POST /chat`) atiende tres tipos de evento, siguiendo el
contrato que implementó frontend (`frontend/A2UI-INTEGRATION.md`):
`"overview"` (al abrir la app), `"message"` (pregunta en lenguaje natural) y
`"action"` (el usuario pulsó algo de la UI generada).

Flujo de una pregunta:

0. El router clasifica la intención Y extrae el periodo en UNA sola llamada
   estructurada. Va junto a propósito: separarlo subiría el costo de 2 a 3
   llamadas por consulta, y la cuota de Gemini es limitada.
1. Python aplica el tope de 3 meses de forma determinística -- no se le
   confía la aritmética de fechas al modelo.
2. El handler de esa intención llama su tool MCP. El agente nunca clasifica
   ni agrega transacciones: esa lógica vive entera en el servidor MCP
   (contrato en español, interno).
3. Gemini decide la presentación (pie_chart / bar_chart y un texto breve)
   usando solo los totales por categoría, no la lista de transacciones.
4. Python traduce el resultado al envelope A2UI en inglés que el frontend
   espera, con las transacciones anidadas por categoría.

**El ciclo se cierra en `event:"action"`** (regla 3 del reto): el agente
ejecuta la acción vía MCP y responde con una PANTALLA NUEVA, no con un
`{ok:true}`. Hoy la acción soportada es `crear_limite_gasto`, que el propio
agente ofrece con un `action_button` cuando una categoría domina el gasto.

Decisión de equipo (2026-09-12): el drill-down de categoría es 100% local
en el frontend -- por eso cada categoría ya trae su `transactions` completa
desde esta respuesta, y el envelope NO incluye acciones `category_click`.
Es una excepción deliberada al ciclo, por robustez en el momento más
visible de la demo; el ciclo sí se cierra en el flujo de acción.

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

import asyncio
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
from google.genai import errors as genai_errors
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
#
# `or "*"` y no `.get(..., "*")`: si CORS_ORIGINS está definida pero vacía
# (ej. una plantilla de .env sin comentar), .get() regresa "" en vez del
# default -- "".split(",") da [''], que no matchea ningún origen real, y
# CORS bloquea absolutamente todo sin ningún error obvio del lado del
# servidor (el navegador solo dice "no se pudo conectar").
app.add_middleware(
    CORSMiddleware,
    allow_origins=(os.environ.get("CORS_ORIGINS") or "*").split(","),
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# --- Clientes de Gemini con rotación de keys -------------------------------
# La capa gratis da 20 solicitudes/día por key, y cada consulta del usuario
# cuesta 2 llamadas. Rotamos entre varias keys al recibir un 429 para no
# quedarnos sin cuota a media demo (ver CLAUDE.md, sección 6).


def _keys_configuradas() -> list[str]:
    """Lee las keys de GEMINI_API_KEYS o GEMINI_API_KEY, indistintamente.

    Ambos nombres aceptan varias separadas por comas: poner la lista en la
    variable en singular es un error fácil de cometer, y si se tomara el
    texto completo como una sola key fallaría cada llamada por credencial
    inválida, que es de las cosas más molestas de diagnosticar.
    """
    crudo = os.environ.get("GEMINI_API_KEYS", "") or os.environ.get("GEMINI_API_KEY", "")
    return [k.strip() for k in crudo.split(",") if k.strip()]


_KEYS = _keys_configuradas()
if not _KEYS:
    raise RuntimeError("Falta GEMINI_API_KEYS (o GEMINI_API_KEY) en el entorno")

_clientes: dict[int, genai.Client] = {}
_key_actual = 0


def _cliente() -> genai.Client:
    if _key_actual not in _clientes:
        _clientes[_key_actual] = genai.Client(api_key=_KEYS[_key_actual])
    return _clientes[_key_actual]


REINTENTOS_503 = 2
ESPERA_503_SEGUNDOS = 1.5


async def _generar_json(prompt: str, schema: types.Schema) -> Any:
    """Una llamada a Gemini con salida JSON estructurada.

    Todas las llamadas al modelo pasan por aquí: así el manejo de errores
    aplica a todo el agente sin repetirlo en cada sitio.

    - 429 (cuota agotada): rota a la siguiente key configurada.
    - 503 (alta demanda): Google mismo lo documenta como "usually
      temporary" -- reintenta un par de veces con una espera corta antes
      de rendirse, en vez de propagar el error crudo al usuario en el
      primer bache pasajero (encontrado probando en vivo: dos 503
      seguidos tumbaron la consulta sin necesidad).
    """
    global _key_actual
    for intento in range(REINTENTOS_503 + 1):
        try:
            for _ in range(len(_KEYS)):
                try:
                    response = await _cliente().aio.models.generate_content(
                        model=MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=schema,
                        ),
                    )
                    return json.loads(response.text)
                except genai_errors.ClientError as exc:
                    if exc.code != 429:
                        raise
                    _key_actual = (_key_actual + 1) % len(_KEYS)
            raise RuntimeError(
                f"Se agotó la cuota diaria de las {len(_KEYS)} API keys configuradas."
            )
        except genai_errors.ServerError as exc:
            if exc.code != 503 or intento == REINTENTOS_503:
                raise RuntimeError(
                    "Gemini no está disponible en este momento (alta demanda). "
                    "Intenta de nuevo en unos segundos."
                ) from exc
            await asyncio.sleep(ESPERA_503_SEGUNDOS)


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


# --- Paso 0: router de intención -------------------------------------------
# Intención Y parámetros en UNA sola llamada, a propósito: separarlo subiría
# el costo por consulta de 2 a 3 llamadas, y la cuota es limitada.

INTENCIONES = [
    "gasto_por_categoria",
    "diagnostico_financiero",
    "proximos_pagos",
    "fuera_de_alcance",
]

ROUTER_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "intencion": types.Schema(type=types.Type.STRING, enum=INTENCIONES),
        "fecha_inicio": types.Schema(type=types.Type.STRING, nullable=True, description="YYYY-MM-DD"),
        "fecha_fin": types.Schema(type=types.Type.STRING, nullable=True, description="YYYY-MM-DD"),
    },
    required=["intencion"],
)


async def _clasificar_intencion(mensaje_usuario: str) -> dict:
    hoy = date.today()
    prompt = f"""Hoy es {hoy.isoformat()}.

Eres el router de un asistente financiero. El usuario escribió:
"{mensaje_usuario}"

Clasifica su intención en UNA de estas:

- "gasto_por_categoria": quiere ver en qué se le fue el dinero, cuánto
  gastó, o el desglose por categoría de un periodo.
- "diagnostico_financiero": quiere saber cómo va, si va bien o mal, si se
  está pasando, comparar contra antes, o consejos sobre sus hábitos.
- "proximos_pagos": pregunta por cargos o pagos que vienen, suscripciones,
  domiciliaciones o qué se le va a cobrar.
- "fuera_de_alcance": cualquier otra cosa (temas no financieros, o
  financieros que este asistente no cubre como inversiones, créditos o
  seguros).

Si la intención necesita un periodo (las dos primeras), interpreta también
el rango de fechas al que se refiere y devuélvelo en fecha_inicio y
fecha_fin (YYYY-MM-DD). Si no menciona fechas, usa el mes actual completo.
Si la intención no necesita periodo, déjalos en null. No te preocupes por
ningún límite máximo de rango: eso se aplica después."""

    return await _generar_json(prompt, ROUTER_SCHEMA)


def _aplicar_tope(solicitado_inicio: date, solicitado_fin: date) -> tuple[date, date, bool]:
    hoy = date.today()
    tope_minimo = hoy - timedelta(days=TOPE_MESES * 31)
    inicio_real = max(solicitado_inicio, tope_minimo)
    # El router a veces resuelve "el mes actual" como el mes completo
    # (ej. hasta el día 30 aunque hoy sea el 12) -- data.py genera
    # transacciones de forma determinista por fecha, sin saber qué es "hoy",
    # así que felizmente fabricaría gasto de días que todavía no pasan en
    # la historia. Nunca se debe pedir más allá de hoy.
    fin_real = min(solicitado_fin, hoy)
    fue_recortado = inicio_real != solicitado_inicio or fin_real != solicitado_fin
    return inicio_real, fin_real, fue_recortado


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

    return await _generar_json(prompt, DECISION_UI_SCHEMA)


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


def _envelope(conversation_id: str, intent: str, components: list[dict], sugerencias: list[str]) -> dict:
    return {
        "version": "1.0",
        "intent": intent,
        "conversation_id": conversation_id,
        "components": components,
        "suggested_prompts": sugerencias,
    }


def _texto(id_componente: str, titulo: str, subtitulo: str | None = None) -> dict:
    props: dict[str, Any] = {"title": titulo}
    if subtitulo:
        props["subtitle"] = subtitulo
    return {"id": id_componente, "type": "text_block", "props": props}


# Sugerencias fijas por intención en vez de generadas por el LLM: cuestan
# cero llamadas (la cuota es limitada) y siguen siendo contextuales, porque
# cambian según la pantalla que se acaba de mostrar.
SUGERENCIAS = {
    "gasto_por_categoria": ["¿Cómo voy este mes?", "¿Qué pagos tengo próximos?"],
    "diagnostico_financiero": ["¿En qué gasté más este mes?", "¿Qué pagos tengo próximos?"],
    "proximos_pagos": ["¿En qué gasté más este mes?", "¿Cómo voy este mes?"],
    "fuera_de_alcance": [
        "¿En qué gasté más este mes?",
        "¿Cómo voy este mes?",
        "¿Qué pagos tengo próximos?",
    ],
    "limite_creado": ["¿Cómo voy este mes?", "¿En qué gasté más?"],
}

# Una categoría "domina" si se lleva al menos esto del total. Regla
# determinista en Python, no decisión del LLM: es lógica de negocio y así
# es testeable y no cuesta tokens.
UMBRAL_DOMINANCIA = 30.0
RECORTE_SUGERIDO = 0.20  # el límite que sugerimos es 20% menos del gasto actual


def _sugerencia_de_limite(categorias: list[dict]) -> dict | None:
    """Arma el action_button de 'crear límite' si una categoría domina el gasto."""
    if not categorias:
        return None
    mayor = max(categorias, key=lambda c: c["total"])
    if mayor["percent"] < UMBRAL_DOMINANCIA:
        return None

    # Redondeado a 50 para que el monto se lea como algo que una persona
    # elegiría, no como un decimal salido de una multiplicación.
    sugerido = round(mayor["total"] * (1 - RECORTE_SUGERIDO) / 50) * 50
    if sugerido <= 0:
        return None

    categoria_interna = next(
        (nombre for nombre, info in CATEGORIA_INFO.items() if info["id"] == mayor["id"]),
        mayor["label"],
    )
    return {
        "id": "sugerencia_limite",
        "type": "action_button",
        "props": {
            "label": f"Crear límite de ${sugerido:,.0f} en {mayor['label']}",
            "action": "crear_limite_gasto",
            "params": {"categoria": categoria_interna, "monto_limite": float(sugerido)},
            "variant": "primary",
        },
    }


# --- Handlers por intención --------------------------------------------------


async def _handler_gasto_por_categoria(
    conversation_id: str, solicitado_inicio: date, solicitado_fin: date
) -> dict:
    fecha_inicio, fecha_fin, fue_recortado = _aplicar_tope(solicitado_inicio, solicitado_fin)

    gasto_por_categoria = await _llamar_tool_mcp(
        "obtener_gasto_por_categoria",
        {"fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()},
    )

    if not gasto_por_categoria:
        # components=[] -- el frontend ya tiene su propio estado vacío
        # ("No hay resultados para esta consulta" + botón volver al resumen).
        return _envelope(conversation_id, "gasto_por_categoria", [], SUGERENCIAS["gasto_por_categoria"])

    total_spent = sum(datos["monto_total"] for datos in gasto_por_categoria.values())
    categorias = _traducir_categorias(gasto_por_categoria, total_spent)
    decision = await _decidir_ui(categorias)

    componentes = [
        _texto("insight", decision["mensaje"]),
        {
            "id": "spending_overview",
            "type": decision["variante"],
            "props": {
                "period": {
                    "start": fecha_inicio.isoformat(),
                    "end": fecha_fin.isoformat(),
                    "requested_start": solicitado_inicio.isoformat(),
                    "requested_end": solicitado_fin.isoformat(),
                    "was_clamped": fue_recortado,
                },
                "total_spent": total_spent,
                "categories": categorias,
            },
        },
    ]

    boton = _sugerencia_de_limite(categorias)
    if boton:
        componentes.append(boton)

    return _envelope(
        conversation_id, "gasto_por_categoria", componentes, SUGERENCIAS["gasto_por_categoria"]
    )


def _etiqueta_categoria(categoria_es: str) -> str:
    return CATEGORIA_INFO.get(categoria_es, {"label": categoria_es})["label"]


def _titulo_diagnostico(diag: dict) -> str:
    """Título del insight -- compuesto en Python, sin gastar otra llamada a Gemini."""
    variacion = diag["variacion_pct"]
    total = diag["total_gastado"]
    if variacion > 0:
        return f"Llevas ${total:,.0f} gastados, {variacion:.0f}% más que el periodo anterior."
    if variacion < 0:
        return f"Llevas ${total:,.0f} gastados, {abs(variacion):.0f}% menos que el periodo anterior."
    return f"Llevas ${total:,.0f} gastados, igual que el periodo anterior."


def _mensaje_riesgo(diag: dict) -> tuple[str, str]:
    """(label, description) del risk_indicator -- prioriza la causa más concreta."""
    limite_excedido = next((l for l in diag["limites"] if l["excedido"]), None)
    if limite_excedido:
        etiqueta = _etiqueta_categoria(limite_excedido["categoria"])
        return (
            "Superaste un límite que creaste",
            f"{etiqueta} lleva ${limite_excedido['gastado']:,.0f}, por encima de tu límite "
            f"de ${limite_excedido['monto_limite']:,.0f}.",
        )

    limite_cerca = next((l for l in diag["limites"] if l["porcentaje_usado"] >= 80), None)
    if limite_cerca:
        etiqueta = _etiqueta_categoria(limite_cerca["categoria"])
        return (
            "Te estás acercando a un límite",
            f"Llevas {limite_cerca['porcentaje_usado']:.0f}% del límite de {etiqueta}.",
        )

    if diag["variacion_pct"] > 10:
        return ("Tu gasto va en aumento", f"Vas {diag['variacion_pct']:.0f}% arriba del periodo anterior.")

    return ("Vas bien este periodo", "Tu gasto se mantiene bajo control.")


def _badge_mayor_gasto(diag: dict) -> dict | None:
    mayor = diag["categoria_mayor_gasto"]
    if not mayor:
        return None
    info = CATEGORIA_INFO.get(mayor["categoria"], {"id": "otros", "label": mayor["categoria"]})
    return {
        "id": "mayor_gasto",
        "type": "category_badge",
        "props": {"category": info["id"], "label": f"Mayor gasto: {info['label']}"},
    }


def _progreso_diagnostico(diag: dict) -> dict | None:
    """progress contra el límite de la categoría de mayor gasto si existe,
    o contra el periodo anterior como referencia si no hay límite guardado."""
    mayor = diag["categoria_mayor_gasto"]
    if mayor:
        limite = next((l for l in diag["limites"] if l["categoria"] == mayor["categoria"]), None)
        if limite:
            return {
                "id": "limite_progreso",
                "type": "progress",
                "props": {
                    "label": f"{_etiqueta_categoria(mayor['categoria'])} vs tu límite",
                    "value": limite["gastado"],
                    "max": limite["monto_limite"],
                },
            }

    anterior_total = diag["periodo_anterior"]["total_gastado"]
    if anterior_total > 0:
        return {
            "id": "comparativo_progreso",
            "type": "progress",
            "props": {
                "label": "Gasto vs el periodo anterior",
                "value": diag["total_gastado"],
                "max": anterior_total,
                # No hay límite guardado -- esto es una referencia, no un
                # presupuesto. "variant": "comparison" evita que el frontend
                # diga "Has superado el objetivo" cuando no existe ningún
                # objetivo que superar.
                "variant": "comparison",
            },
        }
    return None


async def _handler_diagnostico_financiero(
    conversation_id: str, solicitado_inicio: date, solicitado_fin: date
) -> dict:
    fecha_inicio, fecha_fin, _ = _aplicar_tope(solicitado_inicio, solicitado_fin)
    diag = await _llamar_tool_mcp(
        "obtener_diagnostico_financiero",
        {"fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()},
    )

    label, descripcion = _mensaje_riesgo(diag)
    componentes = [
        _texto("diagnostico", _titulo_diagnostico(diag)),
        {
            "id": "riesgo",
            "type": "risk_indicator",
            "props": {"level": diag["nivel_riesgo"], "label": label, "description": descripcion},
        },
    ]

    badge = _badge_mayor_gasto(diag)
    if badge:
        componentes.append(badge)

    progreso = _progreso_diagnostico(diag)
    if progreso:
        componentes.append(progreso)

    return _envelope(
        conversation_id, "diagnostico_financiero", componentes, SUGERENCIAS["diagnostico_financiero"]
    )


async def _handler_proximos_pagos(conversation_id: str) -> dict:
    resultado = await _llamar_tool_mcp("obtener_proximos_pagos", {})
    pagos = resultado["pagos"]

    if not pagos:
        return _envelope(
            conversation_id,
            "proximos_pagos",
            [_texto("insight", "No detecté cargos recurrentes en tus últimos 3 meses.")],
            SUGERENCIAS["proximos_pagos"],
        )

    hoy = date.today()
    transactions = [
        {
            "id": f"p{i}",
            "date": p["fecha_estimada"],
            "description": p["comercio"],
            "amount": -p["monto_estimado"],
        }
        for i, p in enumerate(pagos, start=1)
    ]

    plural = "s" if len(pagos) != 1 else ""
    componentes = [
        _texto("insight", f"Tienes {len(pagos)} cargo{plural} recurrente{plural} detectado{plural}."),
        {
            "id": "pagos",
            "type": "transaction_list",
            "props": {
                # Sin esto, TransactionList.tsx cae en su fallback "Todas las
                # transacciones" -- correcto para un desglose por categoría,
                # pero engañoso aquí (esto no es "todas", son solo los cargos
                # recurrentes proyectados).
                "category": {"id": "proximos_pagos", "label": "Pagos próximos"},
                "period": {
                    "start": hoy.isoformat(),
                    "end": (hoy + timedelta(days=30)).isoformat(),
                    "label": "Próximos 30 días (estimado)",
                },
                "total": resultado["total_estimado"],
                "transactions": transactions,
            },
        },
    ]
    return _envelope(conversation_id, "proximos_pagos", componentes, SUGERENCIAS["proximos_pagos"])


def _handler_fuera_de_alcance(conversation_id: str) -> dict:
    return _envelope(
        conversation_id,
        "fuera_de_alcance",
        [
            _texto(
                "fuera_de_alcance",
                "Eso no lo puedo responder todavía.",
                "Puedo ayudarte con tus gastos, tu diagnóstico financiero y tus próximos pagos.",
            )
        ],
        SUGERENCIAS["fuera_de_alcance"],
    )


# --- Orquestación de consultas ----------------------------------------------


def _periodo_del_router(router: dict) -> tuple[date, date]:
    """Fechas que resolvió el router, con el mes actual como red de seguridad."""
    hoy = date.today()
    try:
        return (
            date.fromisoformat(router["fecha_inicio"]),
            date.fromisoformat(router["fecha_fin"]),
        )
    except (KeyError, TypeError, ValueError):
        return hoy.replace(day=1), hoy


async def _responder_consulta(mensaje_usuario: str | None, conversation_id: str) -> dict:
    hoy = date.today()

    if not mensaje_usuario:
        # event="overview": ya sabemos la intención, así que no gastamos la
        # llamada del router en el caso más común (abrir la app).
        return await _handler_gasto_por_categoria(conversation_id, hoy.replace(day=1), hoy)

    router = await _clasificar_intencion(mensaje_usuario)
    intencion = router.get("intencion", "fuera_de_alcance")

    if intencion == "gasto_por_categoria":
        inicio, fin = _periodo_del_router(router)
        return await _handler_gasto_por_categoria(conversation_id, inicio, fin)

    if intencion == "diagnostico_financiero":
        inicio, fin = _periodo_del_router(router)
        return await _handler_diagnostico_financiero(conversation_id, inicio, fin)

    if intencion == "proximos_pagos":
        return await _handler_proximos_pagos(conversation_id)

    return _handler_fuera_de_alcance(conversation_id)


# --- Orquestación de acciones (aquí se cierra el ciclo) ---------------------


async def _responder_accion(action_id: str, params: dict[str, Any], conversation_id: str) -> dict:
    """Ejecuta la acción y responde con una PANTALLA NUEVA, no con un {ok:true}.

    Eso es lo que cumple la regla 3 del reto: la interacción con la UI
    generada vuelve al agente y produce una interfaz nueva.
    """
    if action_id != "crear_limite_gasto":
        raise HTTPException(status_code=400, detail=f"Acción no soportada: {action_id}")

    categoria = params.get("categoria")
    monto_limite = params.get("monto_limite")
    if not categoria or not monto_limite:
        raise HTTPException(status_code=400, detail="Faltan 'categoria' o 'monto_limite'")

    await _llamar_tool_mcp(
        "crear_limite_gasto", {"categoria": categoria, "monto_limite": float(monto_limite)}
    )

    # Cuánto lleva gastado en esa categoría este mes, para que la
    # confirmación muestre dónde está parado contra el límite recién creado.
    hoy = date.today()
    gasto = await _llamar_tool_mcp(
        "obtener_gasto_por_categoria",
        {"fecha_inicio": hoy.replace(day=1).isoformat(), "fecha_fin": hoy.isoformat()},
    )
    gastado = gasto.get(categoria, {}).get("monto_total", 0.0)
    etiqueta = CATEGORIA_INFO.get(categoria, {}).get("label", categoria)

    return _envelope(
        conversation_id,
        "limite_creado",
        [
            _texto(
                "confirmacion",
                f"Listo, te aviso si {etiqueta} pasa de ${float(monto_limite):,.0f}.",
            ),
            {
                "id": "limite_progreso",
                "type": "progress",
                "props": {
                    "label": f"{etiqueta} este mes",
                    "value": gastado,
                    "max": float(monto_limite),
                },
            },
        ],
        SUGERENCIAS["limite_creado"],
    )


# --- Endpoint HTTP (único punto de contacto del frontend) ------------------


@app.post("/chat")
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    try:
        if req.event == "action":
            return await _responder_accion(req.action_id or "", req.params or {}, conversation_id)
        return await _responder_consulta(req.message, conversation_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
