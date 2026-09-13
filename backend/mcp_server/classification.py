"""Clasificación de transacciones por categoría.

Pipeline por capas (ver CLAUDE.md, secciones 3 y 4): diccionario de cadenas
conocidas -> palabras genéricas -> caché de resultados previos del LLM ->
batch al LLM para lo que quede pendiente -> "Otros" como red de seguridad
final.

Este módulo no importa ningún cliente de Gemini ni de ningún otro LLM: el
fallback se recibe como una función inyectada (`llm_classify_fn`), para
poder probar todo el pipeline con pytest sin red y sin decidir todavía el
SDK exacto (ver CLAUDE.md, sección 6, "por definir"). El Bloque 2
(`agent.py`) es quien construye esa función con el cliente real de Gemini y
se la pasa a `obtener_gasto_por_categoria`.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import Callable

from . import data
from .categorias import CATEGORIAS, TIPOS_NO_GASTO

STORAGE_DIR = Path(__file__).parent / "storage"
CACHE_PATH = STORAGE_DIR / "classification_cache.json"

CATEGORIA_OTROS = "Otros"

# Recibe la lista de conceptos únicos sin resolver y las categorías válidas;
# regresa {concepto: categoria}. Si un concepto no viene en la respuesta, o
# la categoría no es una de las válidas, se trata como no resuelto -> Otros.
LLMClassifyFn = Callable[[list[str], list[str]], dict[str, str]]

# (a) nombres de cadena/comercio conocidos y enumerables: match exacto contra
# el concepto normalizado.
DICCIONARIO_CADENAS: dict[str, str] = {
    "WALMART": "Despensa",
    "SORIANA": "Despensa",
    "CHEDRAUI": "Despensa",
    "HEB": "Despensa",
    "COSTCO": "Despensa",
    "STARBUCKS": "Comidas/Restaurantes",
    "VIPS": "Comidas/Restaurantes",
    "MCDONALDS": "Comidas/Restaurantes",
    "CFE": "Servicios",
    "TELMEX": "Servicios",
    "TELCEL": "Servicios",
    "IZZI": "Servicios",
    "TOTALPLAY": "Servicios",
    "UBER": "Transporte",
    "DIDI": "Transporte",
    "PEMEX": "Transporte",
    "NETFLIX": "Entretenimiento/Suscripciones",
    "SPOTIFY": "Entretenimiento/Suscripciones",
    "DISNEY PLUS": "Entretenimiento/Suscripciones",
    "HBO MAX": "Entretenimiento/Suscripciones",
    "CINEPOLIS": "Entretenimiento/Suscripciones",
    "CINEMEX": "Entretenimiento/Suscripciones",
    "AMAZON": "Compras",
    "LIVERPOOL": "Compras",
    "MERCADO LIBRE": "Compras",
    "SHEIN": "Compras",
}

# (b) palabras genéricas que indican el tipo de negocio: match por substring,
# útil para negocios independientes no enumerables (ver CLAUDE.md, sección 3).
PALABRAS_GENERICAS: dict[str, str] = {
    "TAQUERIA": "Comidas/Restaurantes",
    "PIZZA": "Comidas/Restaurantes",
    "RESTAURANTE": "Comidas/Restaurantes",
    "CAFE": "Comidas/Restaurantes",
    "SUSHI": "Comidas/Restaurantes",
    "TACOS": "Comidas/Restaurantes",
    "FARMACIA": "Salud",
    "CONSULTORIO": "Salud",
    "HOSPITAL": "Salud",
    "CLINICA": "Salud",
    "DENTAL": "Salud",
    "LABORATORIO": "Salud",
    "GASOLINERA": "Transporte",
    "ESTACIONAMIENTO": "Transporte",
    "SUPER": "Despensa",
    "MERCADO": "Despensa",
}


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_acentos.strip().upper()


def _clasificar_por_diccionario(concepto: str) -> str | None:
    normalizado = _normalizar(concepto)
    if normalizado in DICCIONARIO_CADENAS:
        return DICCIONARIO_CADENAS[normalizado]
    for palabra, categoria in PALABRAS_GENERICAS.items():
        if palabra in normalizado:
            return categoria
    return None


def _cargar_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def _guardar_cache(cache: dict[str, str]) -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def clasificar_conceptos(
    conceptos: list[str], llm_classify_fn: LLMClassifyFn | None = None
) -> dict[str, str]:
    """Resuelve la categoría de cada concepto único.

    Orden: diccionario -> caché persistente -> batch al LLM (una sola
    llamada con todos los pendientes, no una por transacción) -> "Otros".
    """
    cache = _cargar_cache()
    resultado: dict[str, str] = {}
    pendientes: list[str] = []

    for concepto in conceptos:
        categoria = _clasificar_por_diccionario(concepto) or cache.get(concepto)
        if categoria is not None:
            resultado[concepto] = categoria
        elif concepto not in pendientes:
            pendientes.append(concepto)

    respuestas = None
    if pendientes and llm_classify_fn is not None:
        try:
            respuestas = llm_classify_fn(pendientes, CATEGORIAS)
        except Exception:
            # Cuota agotada (429), red caída, lo que sea: la consulta completa
            # no debe tumbarse por esto. Los pendientes caen en Otros para
            # esta respuesta, pero NO se cachean -- una falla transitoria no
            # debe condenar un concepto a Otros para siempre.
            respuestas = None

    if respuestas is not None:
        for concepto in pendientes:
            categoria = respuestas.get(concepto)
            resultado[concepto] = categoria if categoria in CATEGORIAS else CATEGORIA_OTROS
            cache[concepto] = resultado[concepto]
        _guardar_cache(cache)
    else:
        for concepto in pendientes:
            resultado[concepto] = CATEGORIA_OTROS

    return resultado


def obtener_gasto_por_categoria(
    fecha_inicio: date,
    fecha_fin: date,
    llm_classify_fn: LLMClassifyFn | None = None,
) -> dict[str, dict]:
    """Contrato Bloque 1 (ver CLAUDE.md, sección 7).

    {"Despensa": {"monto_total": 1234.50,
                  "transacciones": [{"fecha": ..., "comercio": ..., "monto": ...}, ...]},
     ...}

    Excluye movimientos no-gasto (retiros, transferencias, depósitos,
    comisiones) antes de clasificar: nunca caen en "Otros".
    """
    transacciones = [
        t
        for t in data.obtener_transacciones(fecha_inicio, fecha_fin)
        if t.tipo_movimiento not in TIPOS_NO_GASTO
    ]

    conceptos_unicos = sorted({t.comercio for t in transacciones})
    categoria_por_concepto = clasificar_conceptos(conceptos_unicos, llm_classify_fn)

    agregado: dict[str, dict] = {}
    for t in transacciones:
        categoria = categoria_por_concepto[t.comercio]
        bucket = agregado.setdefault(categoria, {"monto_total": 0.0, "transacciones": []})
        bucket["monto_total"] = round(bucket["monto_total"] + t.monto, 2)
        bucket["transacciones"].append(
            {"fecha": t.fecha.isoformat(), "comercio": t.comercio, "monto": t.monto}
        )

    return agregado
