"""Pruebas de obtener_diagnostico_financiero y obtener_proximos_pagos.

A diferencia de test_data.py, aquí NO se usa el generador aleatorio de
data.py: se controla `data.obtener_transacciones`/`obtener_limites_gasto`
con monkeypatch para que cada caso sea determinista e interpretable (saber
exactamente por qué el nivel de riesgo salió "high" y no "medium").
"""
from datetime import date

import pytest

from mcp_server import classification
from mcp_server.data import Transaccion


@pytest.fixture
def cache_aislada(tmp_path, monkeypatch):
    monkeypatch.setattr(classification, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(classification, "CACHE_PATH", tmp_path / "classification_cache.json")


@pytest.fixture
def hoy_fijo(monkeypatch):
    """Fija 'hoy' para las pruebas de obtener_proximos_pagos, que filtra
    cualquier fecha proyectada anterior a hoy (ver classification.py)."""

    class FechaFija(date):
        @classmethod
        def today(cls):
            return date(2026, 9, 12)

    monkeypatch.setattr(classification, "date", FechaFija)


def _transacciones_por_rango(mapa: dict[tuple[date, date], list[Transaccion]]):
    """Fake de data.obtener_transacciones que regresa una lista fija por rango exacto."""

    def fake(fecha_inicio, fecha_fin):
        return mapa.get((fecha_inicio, fecha_fin), [])

    return fake


# --- obtener_diagnostico_financiero ------------------------------------------


def test_diagnostico_variacion_positiva_cuando_gasto_mas_que_antes(monkeypatch, cache_aislada):
    actual = [Transaccion(date(2026, 9, 5), "WALMART", 1000.0, "compra")]
    anterior = [Transaccion(date(2026, 8, 5), "WALMART", 500.0, "compra")]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones",
        _transacciones_por_rango(
            {
                (date(2026, 9, 1), date(2026, 9, 30)): actual,
                (date(2026, 8, 2), date(2026, 8, 31)): anterior,
            }
        ),
    )
    monkeypatch.setattr("mcp_server.classification.data.obtener_limites_gasto", lambda: [])

    diag = classification.obtener_diagnostico_financiero(date(2026, 9, 1), date(2026, 9, 30))

    assert diag["total_gastado"] == 1000.0
    assert diag["periodo_anterior"]["total_gastado"] == 500.0
    assert diag["variacion_pct"] == 100.0
    assert diag["categoria_mayor_gasto"]["categoria"] == "Despensa"


def test_diagnostico_riesgo_alto_por_variacion_mayor_a_25_por_ciento(monkeypatch, cache_aislada):
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones",
        _transacciones_por_rango(
            {
                (date(2026, 9, 1), date(2026, 9, 30)): [
                    Transaccion(date(2026, 9, 5), "WALMART", 1300.0, "compra")
                ],
                (date(2026, 8, 2), date(2026, 8, 31)): [
                    Transaccion(date(2026, 8, 5), "WALMART", 1000.0, "compra")
                ],
            }
        ),
    )
    monkeypatch.setattr("mcp_server.classification.data.obtener_limites_gasto", lambda: [])

    diag = classification.obtener_diagnostico_financiero(date(2026, 9, 1), date(2026, 9, 30))

    assert diag["variacion_pct"] == 30.0
    assert diag["nivel_riesgo"] == "high"


def test_diagnostico_riesgo_alto_por_limite_excedido_aunque_no_haya_variacion(
    monkeypatch, cache_aislada
):
    transacciones = [Transaccion(date(2026, 9, 5), "WALMART", 1000.0, "compra")]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones",
        _transacciones_por_rango(
            {
                (date(2026, 9, 1), date(2026, 9, 30)): transacciones,
                (date(2026, 8, 2), date(2026, 8, 31)): transacciones,
            }
        ),
    )
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_limites_gasto",
        lambda: [{"categoria": "Despensa", "monto_limite": 800.0, "creado_en": "x"}],
    )

    diag = classification.obtener_diagnostico_financiero(date(2026, 9, 1), date(2026, 9, 30))

    assert diag["variacion_pct"] == 0.0
    assert diag["limites"][0]["excedido"] is True
    assert diag["nivel_riesgo"] == "high"


def test_diagnostico_riesgo_medio_por_limite_cerca_de_80_por_ciento(monkeypatch, cache_aislada):
    transacciones = [Transaccion(date(2026, 9, 5), "WALMART", 850.0, "compra")]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones",
        _transacciones_por_rango(
            {
                (date(2026, 9, 1), date(2026, 9, 30)): transacciones,
                (date(2026, 8, 2), date(2026, 8, 31)): transacciones,
            }
        ),
    )
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_limites_gasto",
        lambda: [{"categoria": "Despensa", "monto_limite": 1000.0, "creado_en": "x"}],
    )

    diag = classification.obtener_diagnostico_financiero(date(2026, 9, 1), date(2026, 9, 30))

    assert diag["limites"][0]["porcentaje_usado"] == 85.0
    assert diag["limites"][0]["excedido"] is False
    assert diag["nivel_riesgo"] == "medium"


def test_diagnostico_riesgo_bajo_sin_limites_ni_variacion_relevante(monkeypatch, cache_aislada):
    transacciones = [Transaccion(date(2026, 9, 5), "WALMART", 1000.0, "compra")]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones",
        _transacciones_por_rango(
            {
                (date(2026, 9, 1), date(2026, 9, 30)): transacciones,
                (date(2026, 8, 2), date(2026, 8, 31)): transacciones,
            }
        ),
    )
    monkeypatch.setattr("mcp_server.classification.data.obtener_limites_gasto", lambda: [])

    diag = classification.obtener_diagnostico_financiero(date(2026, 9, 1), date(2026, 9, 30))

    assert diag["nivel_riesgo"] == "low"


def test_diagnostico_sin_gasto_en_ningun_periodo_no_revienta(monkeypatch, cache_aislada):
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", _transacciones_por_rango({})
    )
    monkeypatch.setattr("mcp_server.classification.data.obtener_limites_gasto", lambda: [])

    diag = classification.obtener_diagnostico_financiero(date(2026, 9, 1), date(2026, 9, 30))

    assert diag["total_gastado"] == 0.0
    assert diag["variacion_pct"] == 0.0
    assert diag["categoria_mayor_gasto"] is None
    assert diag["nivel_riesgo"] == "low"


# --- obtener_proximos_pagos --------------------------------------------------


def test_proximos_pagos_detecta_recurrencia_en_2_de_3_meses(monkeypatch, cache_aislada, hoy_fijo):
    transacciones = [
        Transaccion(date(2026, 8, 9), "NETFLIX", 180.0, "compra"),
        Transaccion(date(2026, 9, 9), "NETFLIX", 180.0, "compra"),
    ]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", lambda ini, fin: transacciones
    )

    pagos = classification.obtener_proximos_pagos()

    assert len(pagos["pagos"]) == 1
    pago = pagos["pagos"][0]
    assert pago["comercio"] == "NETFLIX"
    assert pago["categoria"] == "Entretenimiento/Suscripciones"
    assert pago["fecha_estimada"] == "2026-10-09"
    assert pago["ocurrencias"] == 2


def test_proximos_pagos_excluye_proyeccion_que_ya_paso(monkeypatch, cache_aislada, hoy_fijo):
    # Última vez en julio: la próxima proyectada (agosto) ya pasó respecto a
    # "hoy" (12 de septiembre) -- la recurrencia probablemente se cortó, o
    # solo falta ver el cargo más reciente. De cualquier forma no es un
    # "próximo" pago.
    transacciones = [
        Transaccion(date(2026, 6, 9), "NETFLIX", 180.0, "compra"),
        Transaccion(date(2026, 7, 9), "NETFLIX", 180.0, "compra"),
    ]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", lambda ini, fin: transacciones
    )

    pagos = classification.obtener_proximos_pagos()

    assert pagos["pagos"] == []


def test_proximos_pagos_excluye_una_sola_ocurrencia(monkeypatch, cache_aislada):
    transacciones = [Transaccion(date(2026, 8, 9), "NETFLIX", 180.0, "compra")]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", lambda ini, fin: transacciones
    )

    pagos = classification.obtener_proximos_pagos()

    assert pagos["pagos"] == []
    assert pagos["total_estimado"] == 0.0


def test_proximos_pagos_excluye_montos_muy_dispersos(monkeypatch, cache_aislada):
    # Mismo comercio, 2 meses, pero montos radicalmente distintos -- no es
    # un cargo fijo, es una coincidencia de compras variables.
    transacciones = [
        Transaccion(date(2026, 7, 9), "AMAZON", 50.0, "compra"),
        Transaccion(date(2026, 8, 9), "AMAZON", 2000.0, "compra"),
    ]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", lambda ini, fin: transacciones
    )

    pagos = classification.obtener_proximos_pagos()

    assert pagos["pagos"] == []


def test_proximos_pagos_excluye_movimientos_no_gasto(monkeypatch, cache_aislada):
    transacciones = [
        Transaccion(date(2026, 7, 9), "TRANSFERENCIA SPEI", 500.0, "transferencia"),
        Transaccion(date(2026, 8, 9), "TRANSFERENCIA SPEI", 500.0, "transferencia"),
    ]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", lambda ini, fin: transacciones
    )

    pagos = classification.obtener_proximos_pagos()

    assert pagos["pagos"] == []


def test_proximos_pagos_estima_fecha_al_mes_siguiente_recortando_dia_invalido(
    monkeypatch, cache_aislada, hoy_fijo
):
    # 31 de enero -> 31 de febrero no existe, debe caer en el 28.
    transacciones = [
        Transaccion(date(2026, 12, 31), "NETFLIX", 180.0, "compra"),
        Transaccion(date(2027, 1, 31), "NETFLIX", 180.0, "compra"),
    ]
    monkeypatch.setattr(
        "mcp_server.classification.data.obtener_transacciones", lambda ini, fin: transacciones
    )

    pagos = classification.obtener_proximos_pagos()

    assert pagos["pagos"][0]["fecha_estimada"] == "2027-02-28"
