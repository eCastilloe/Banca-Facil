"""Capa de datos: transacciones sintéticas + persistencia de límites de gasto.

Módulo aislado y reemplazable (ver CLAUDE.md, sección 4): el resto del
sistema solo conoce `obtener_transacciones` y `crear_limite_gasto`. Si algún
día se conecta una API real de Banorte/Open Finance, solo este archivo
cambia.

Las transacciones NO se persisten a disco: se generan de forma determinista
(semilla fija por día) cada vez que se piden, así que siempre reflejan la
ventana móvil de hasta 3 meses hacia atrás desde "hoy" sin quedar obsoletas.
Los límites de gasto sí se persisten, porque son estado real creado por el
usuario.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .categorias import CATEGORIAS

STORAGE_DIR = Path(__file__).parent / "storage"
LIMITES_PATH = STORAGE_DIR / "limites_gasto.json"

MESES_HISTORIAL_MAX = 3
DIAS_HISTORIAL_MAX = MESES_HISTORIAL_MAX * 30
SEMILLA_BASE = 42

# (comercio, tipo_movimiento, (monto_min, monto_max))
# tipo_movimiento "compra" = gasto discrecional; el resto se excluye del
# desglose por categoría (ver categorias.TIPOS_NO_GASTO).
COMERCIOS_SINTETICOS: list[tuple[str, str, tuple[float, float]]] = [
    ("WALMART", "compra", (200, 1800)),
    ("SORIANA", "compra", (150, 1500)),
    ("HEB", "compra", (200, 2000)),
    ("STARBUCKS", "compra", (60, 180)),
    ("VIPS", "compra", (150, 450)),
    ("TAQUERIA EL BUEN SABOR", "compra", (80, 250)),
    ("PIZZA REGIA", "compra", (150, 500)),
    ("CFE", "compra", (300, 900)),
    ("TELMEX", "compra", (400, 700)),
    ("UBER", "compra", (60, 300)),
    ("DIDI", "compra", (50, 280)),
    ("GASOLINERA PEMEX", "compra", (400, 1200)),
    ("NETFLIX", "compra", (139, 219)),
    ("SPOTIFY", "compra", (115, 165)),
    ("FARMACIA GUADALAJARA", "compra", (80, 600)),
    ("CONSULTORIO DR. LOPEZ", "compra", (400, 1200)),
    ("AMAZON", "compra", (150, 2500)),
    ("LIVERPOOL", "compra", (300, 3500)),
    ("RETIRO CAJERO", "retiro", (500, 3000)),
    ("TRANSFERENCIA SPEI", "transferencia", (200, 5000)),
    ("DEPOSITO NOMINA", "deposito", (8000, 15000)),
    ("COMISION MANEJO DE CUENTA", "comision", (0, 200)),
]


@dataclass(frozen=True)
class Transaccion:
    fecha: date
    comercio: str
    monto: float
    tipo_movimiento: str


def _movimientos_del_dia(dia: date) -> list[Transaccion]:
    """Genera las transacciones de un día concreto de forma determinista.

    La semilla depende solo de la fecha (no de cuándo se llama), así que el
    mismo día siempre produce las mismas transacciones sin importar si se
    consulta hoy o mañana.
    """
    rng = random.Random(SEMILLA_BASE + dia.toordinal())
    movimientos = []
    for _ in range(rng.randint(0, 3)):
        comercio, tipo, (monto_min, monto_max) = rng.choice(COMERCIOS_SINTETICOS)
        monto = round(rng.uniform(monto_min, monto_max), 2)
        movimientos.append(Transaccion(dia, comercio, monto, tipo))
    return movimientos


def obtener_transacciones(fecha_inicio: date, fecha_fin: date) -> list[Transaccion]:
    """Transacciones crudas (sin clasificar) en el rango [fecha_inicio, fecha_fin].

    No aplica el tope de 3 meses aquí: ese tope lo resuelve el agente sobre
    el rango en lenguaje natural (ver CLAUDE.md, sección 3, paso 1) antes de
    llamar a esta función.
    """
    if fecha_fin < fecha_inicio:
        raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")

    transacciones: list[Transaccion] = []
    dia = fecha_inicio
    while dia <= fecha_fin:
        transacciones.extend(_movimientos_del_dia(dia))
        dia += timedelta(days=1)
    return transacciones


def _leer_limites() -> list[dict]:
    if not LIMITES_PATH.exists():
        return []
    return json.loads(LIMITES_PATH.read_text(encoding="utf-8"))


def _guardar_limites(limites: list[dict]) -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    LIMITES_PATH.write_text(
        json.dumps(limites, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def crear_limite_gasto(categoria: str, monto_limite: float) -> dict:
    """Crea (o reemplaza) el límite de gasto guardado para una categoría.

    Contrato Bloque 1 (ver CLAUDE.md, sección 7).
    """
    if categoria not in CATEGORIAS:
        raise ValueError(f"categoria inválida: {categoria!r}. Debe ser una de {CATEGORIAS}")
    if monto_limite <= 0:
        raise ValueError("monto_limite debe ser positivo")

    limite = {
        "categoria": categoria,
        "monto_limite": monto_limite,
        "creado_en": datetime.now().isoformat(),
    }
    limites = [l for l in _leer_limites() if l["categoria"] != categoria]
    limites.append(limite)
    _guardar_limites(limites)
    return {"ok": True, "limite": limite}


def obtener_limites_gasto() -> list[dict]:
    """Todos los límites de gasto guardados hasta ahora."""
    return _leer_limites()
