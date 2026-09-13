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

import calendar
import json
import os
import unicodedata
from datetime import date, timedelta
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
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Caché corrupta (misma idea que data._leer_limites): se pierde el
        # ahorro de llamadas ya resueltas, pero no debe tumbar cada consulta
        # -- simplemente se vuelve a preguntar al LLM lo que ya se sabía.
        return {}


def _guardar_cache(cache: dict[str, str]) -> None:
    """Escritura atómica -- ver el docstring de `data._guardar_limites`."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE_PATH.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    os.replace(tmp_path, CACHE_PATH)


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


# Umbrales del nivel de riesgo -- regla de negocio determinista, no decisión
# del LLM: así es testeable y no cuesta tokens (ver CLAUDE.md, sección 11.2).
VARIACION_ALTA_PCT = 25.0
VARIACION_MEDIA_PCT = 10.0
LIMITE_CERCA_PCT = 80.0


def obtener_diagnostico_financiero(
    fecha_inicio: date,
    fecha_fin: date,
    llm_classify_fn: LLMClassifyFn | None = None,
) -> dict:
    """Contrato en CLAUDE.md, sección 11.2.

    Compara el periodo pedido contra el periodo inmediato anterior de la
    misma duración, evalúa los límites guardados contra el gasto actual, y
    calcula un nivel de riesgo determinista.
    """
    actual = obtener_gasto_por_categoria(fecha_inicio, fecha_fin, llm_classify_fn)
    total_actual = round(sum(d["monto_total"] for d in actual.values()), 2)

    duracion = (fecha_fin - fecha_inicio).days + 1
    fin_anterior = fecha_inicio - timedelta(days=1)
    inicio_anterior = fin_anterior - timedelta(days=duracion - 1)
    anterior = obtener_gasto_por_categoria(inicio_anterior, fin_anterior, llm_classify_fn)
    total_anterior = round(sum(d["monto_total"] for d in anterior.values()), 2)

    if total_anterior > 0:
        variacion_pct = round((total_actual - total_anterior) / total_anterior * 100, 1)
    else:
        variacion_pct = 100.0 if total_actual > 0 else 0.0

    categoria_mayor_gasto = None
    if actual:
        nombre, datos = max(actual.items(), key=lambda kv: kv[1]["monto_total"])
        porcentaje = round(datos["monto_total"] / total_actual * 100, 1) if total_actual else 0.0
        categoria_mayor_gasto = {
            "categoria": nombre,
            "monto_total": datos["monto_total"],
            "porcentaje": porcentaje,
        }

    limites = []
    for limite in data.obtener_limites_gasto():
        categoria = limite["categoria"]
        monto_limite = limite["monto_limite"]
        gastado = actual.get(categoria, {}).get("monto_total", 0.0)
        porcentaje_usado = round(gastado / monto_limite * 100, 1) if monto_limite else 0.0
        limites.append(
            {
                "categoria": categoria,
                "monto_limite": monto_limite,
                "gastado": gastado,
                "porcentaje_usado": porcentaje_usado,
                "excedido": gastado > monto_limite,
            }
        )

    algun_limite_excedido = any(l["excedido"] for l in limites)
    algun_limite_cerca = any(l["porcentaje_usado"] >= LIMITE_CERCA_PCT for l in limites)

    if algun_limite_excedido or variacion_pct > VARIACION_ALTA_PCT:
        nivel_riesgo = "high"
    elif algun_limite_cerca or variacion_pct > VARIACION_MEDIA_PCT:
        nivel_riesgo = "medium"
    else:
        nivel_riesgo = "low"

    return {
        "periodo": {"inicio": fecha_inicio.isoformat(), "fin": fecha_fin.isoformat()},
        "total_gastado": total_actual,
        "periodo_anterior": {
            "inicio": inicio_anterior.isoformat(),
            "fin": fin_anterior.isoformat(),
            "total_gastado": total_anterior,
        },
        "variacion_pct": variacion_pct,
        "categoria_mayor_gasto": categoria_mayor_gasto,
        "limites": limites,
        "nivel_riesgo": nivel_riesgo,
    }


# "Monto parecido" para considerar un cargo recurrente: el rango entre el
# monto más alto y el más bajo no puede superar este porcentaje del
# promedio. Filtra compras variables (Despensa, Compras) que por azar caen
# en 2-3 meses distintos, sin excluir servicios reales (CFE/TELMEX varían
# de un mes a otro, pero no tanto como una compra discrecional).
DISPERSION_MAXIMA = 0.8
MESES_HISTORIAL_PAGOS = 3

# "≥2 de 3 meses con monto parecido" no alcanza para distinguir una
# suscripción real de una tienda a la que simplemente vuelves seguido
# (Starbucks y Spotify tienen una firma estadística casi idéntica: monto
# angosto, aparece cada mes). Restringir a las categorías que por
# definición son gasto recurrente -- mismo principio que el diccionario de
# clasificación: usar lo que ya sabemos del dominio en vez de solo
# estadística sobre los montos.
CATEGORIAS_RECURRENTES = {"Servicios", "Entretenimiento/Suscripciones"}


def _sumar_un_mes(fecha: date) -> date:
    """Mismo día del mes siguiente, recortado si ese mes es más corto."""
    if fecha.month == 12:
        anio, mes = fecha.year + 1, 1
    else:
        anio, mes = fecha.year, fecha.month + 1
    ultimo_dia_del_mes = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(fecha.day, ultimo_dia_del_mes))


def obtener_proximos_pagos(llm_classify_fn: LLMClassifyFn | None = None) -> dict:
    """Contrato en CLAUDE.md, sección 11.2.

    Detecta cargos recurrentes en los últimos 3 meses -- mismo comercio en
    al menos 2 meses distintos, con montos parecidos, Y clasificado en una
    categoría de gasto recurrente por naturaleza (Servicios,
    Entretenimiento/Suscripciones) -- y proyecta la próxima fecha y monto.
    Sale de las transacciones que ya existen -- no inventa un dominio de
    datos nuevo ni persiste nada.
    """
    hoy = date.today()
    inicio = hoy - timedelta(days=30 * MESES_HISTORIAL_PAGOS)
    transacciones = [
        t for t in data.obtener_transacciones(inicio, hoy) if t.tipo_movimiento not in TIPOS_NO_GASTO
    ]

    por_comercio: dict[str, list] = {}
    for t in transacciones:
        por_comercio.setdefault(t.comercio, []).append(t)

    # Clasificar antes de filtrar por recurrencia: la categoría es la
    # primera criba (¿este comercio siquiera puede ser un cargo fijo?), más
    # barata que calcular dispersión de montos para algo que se va a
    # descartar de todas formas.
    categoria_por_concepto = clasificar_conceptos(sorted(por_comercio), llm_classify_fn)

    candidatos = []
    for comercio, movimientos in por_comercio.items():
        if categoria_por_concepto[comercio] not in CATEGORIAS_RECURRENTES:
            continue

        meses_distintos = {(t.fecha.year, t.fecha.month) for t in movimientos}
        if len(meses_distintos) < 2:
            continue

        montos = [t.monto for t in movimientos]
        promedio = sum(montos) / len(montos)
        dispersion = (max(montos) - min(montos)) / promedio if promedio else 0.0
        if dispersion > DISPERSION_MAXIMA:
            continue

        ultima = max(movimientos, key=lambda t: t.fecha)
        proxima_fecha = _sumar_un_mes(ultima.fecha)
        if proxima_fecha < hoy:
            # El comercio no volvió a aparecer en el mes más reciente: la
            # recurrencia probablemente se cortó, o solo nos falta ver el
            # cargo más nuevo. De cualquier forma, una fecha "próxima" que
            # ya pasó no es un próximo pago -- mejor omitirlo que confundir.
            continue
        candidatos.append(
            {
                "comercio": comercio,
                "ultima_fecha": ultima.fecha,
                "proxima_fecha": proxima_fecha,
                "monto_estimado": round(promedio, 2),
                "ocurrencias": len(movimientos),
            }
        )

    pagos = [
        {
            "comercio": c["comercio"],
            "categoria": categoria_por_concepto[c["comercio"]],
            "monto_estimado": c["monto_estimado"],
            "fecha_estimada": c["proxima_fecha"].isoformat(),
            "ultima_fecha": c["ultima_fecha"].isoformat(),
            "ocurrencias": c["ocurrencias"],
        }
        for c in candidatos
    ]
    pagos.sort(key=lambda p: p["fecha_estimada"])

    return {"pagos": pagos, "total_estimado": round(sum(p["monto_estimado"] for p in pagos), 2)}
