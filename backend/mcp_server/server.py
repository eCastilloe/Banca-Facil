"""Servidor MCP del flujo de control de gasto por categoría (Bloque 2).

Wrappers finos sobre el Bloque 1 real (`data.py` + `classification.py`) --
sin lógica de negocio propia aquí (CLAUDE.md, sección 7).

El fallback a LLM para clasificación (CLAUDE.md sección 3, paso 3) se
construye en este archivo y no en `agent.py`: `classification.py` recibe
esa función inyectada (`llm_classify_fn`) y la ejecuta DENTRO de este
proceso -- el del servidor MCP, que corre separado de `agent.py` y se
conecta por stdio. No hay forma de "pasar una función de Python" de un
proceso a otro por MCP, solo argumentos serializables -- así que el cliente
de Gemini para este fallback tiene que vivir aquí, con su propia llamada
estructurada (independiente de la que hace `agent.py` para periodo/UI).

En la práctica, el diccionario + palabras genéricas de `classification.py`
ya cubren todos los comercios sintéticos de `data.py`, así que este
fallback casi nunca se dispara con los datos de la demo -- pero existe para
comercios reales no enumerables (ver CLAUDE.md, sección 4).
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp.server.fastmcp import FastMCP

from . import classification, data

load_dotenv()

mcp = FastMCP("control-gasto-categoria")

TOPE_MESES = 3

_gemini_client: genai.Client | None = None


def _primera_key() -> str:
    """Acepta `GEMINI_API_KEYS` (plural) o `GEMINI_API_KEY`, igual que el agente.

    Este proceso no rota keys como `agent.py`: el fallback de clasificación
    casi nunca se dispara (el diccionario cubre todos los comercios
    sintéticos), así que basta con tomar la primera y no reventar por leer
    la variable equivocada.
    """
    varias = os.environ.get("GEMINI_API_KEYS", "").strip()
    if varias:
        return varias.split(",")[0].strip()
    return os.environ.get("GEMINI_API_KEY", "").strip()


_ITEM_CLASIFICACION = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "concepto": types.Schema(type=types.Type.STRING),
        "categoria": types.Schema(type=types.Type.STRING),
    },
    required=["concepto", "categoria"],
)


def _clasificar_con_gemini(conceptos: list[str], categorias_validas: list[str]) -> dict[str, str]:
    """`LLMClassifyFn` inyectada a `classification.obtener_gasto_por_categoria`.

    Un solo batch para todos los conceptos pendientes (nunca una llamada por
    transacción, ver CLAUDE.md sección 3, paso 3). Si Gemini devuelve una
    categoría fuera de las válidas, `classification.py` ya la recorta a
    "Otros" -- no hay que validar eso aquí.
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=_primera_key())

    prompt = f"""Clasifica cada uno de estos conceptos de transacción bancaria
en UNA de estas categorías válidas: {categorias_validas}.

Conceptos a clasificar (uno por línea):
{chr(10).join(conceptos)}

Responde con un arreglo JSON de objetos {{"concepto": ..., "categoria": ...}},
uno por cada concepto de la lista, en el mismo orden."""

    response = _gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(type=types.Type.ARRAY, items=_ITEM_CLASIFICACION),
        ),
    )
    resultados = json.loads(response.text)
    return {item["concepto"]: item["categoria"] for item in resultados}


@mcp.tool()
def obtener_gasto_por_categoria(fecha_inicio: str, fecha_fin: str) -> dict:
    """Gasto agrupado por categoría en un rango de fechas (YYYY-MM-DD, máx. 3 meses)."""
    inicio = date.fromisoformat(fecha_inicio)
    fin = date.fromisoformat(fecha_fin)
    if fin < inicio:
        raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")

    # Salvaguarda defensiva: el agente ya debe resolver el rango dentro del
    # tope de 3 meses antes de llamar a esta tool. Este clamp es solo una
    # red de seguridad, no la fuente de verdad (CLAUDE.md, sección 3, paso 1).
    tope = fin - timedelta(days=TOPE_MESES * 31)
    if inicio < tope:
        inicio = tope

    return classification.obtener_gasto_por_categoria(inicio, fin, llm_classify_fn=_clasificar_con_gemini)


@mcp.tool()
def crear_limite_gasto(categoria: str, monto_limite: float) -> dict:
    """Crea (o reemplaza) el límite de gasto mensual para una categoría."""
    return data.crear_limite_gasto(categoria, monto_limite)


if __name__ == "__main__":
    mcp.run()
