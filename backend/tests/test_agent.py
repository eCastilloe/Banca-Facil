"""Pruebas de las redes de seguridad de agent.py: timeouts, respuestas del
modelo que no se pueden interpretar, fechas mal resueltas por el router, y
validación del evento de acción. No hay pytest-asyncio como dependencia del
proyecto, así que las corutinas se corren con asyncio.run directamente.

GEMINI_API_KEYS se fija ANTES de importar agent: el módulo revienta al
importarse si esa variable no existe (ver agent.py), y estas pruebas no
deben depender de que exista un backend/.env real con una key de verdad --
nunca se hace ninguna llamada de red aquí, todo lo que toca a Gemini está
monkeypatcheado.
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("GEMINI_API_KEYS", "key-de-prueba-no-real")

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import agent  # noqa: E402


# --- _periodo_del_router / _aplicar_tope: red de seguridad ante un LLM que
# interpreta mal el lenguaje natural ----------------------------------------


def test_periodo_del_router_usa_mes_actual_si_faltan_fechas():
    hoy = date.today()
    inicio, fin = agent._periodo_del_router({"intencion": "diagnostico_financiero"})
    assert (inicio, fin) == (hoy.replace(day=1), hoy)


def test_periodo_del_router_usa_mes_actual_si_json_no_trae_fechas_parseables():
    hoy = date.today()
    inicio, fin = agent._periodo_del_router({"fecha_inicio": "no es una fecha", "fecha_fin": None})
    assert (inicio, fin) == (hoy.replace(day=1), hoy)


def test_periodo_del_router_usa_mes_actual_si_fechas_vienen_invertidas():
    hoy = date.today()
    inicio, fin = agent._periodo_del_router(
        {"fecha_inicio": "2026-09-20", "fecha_fin": "2026-09-01"}
    )
    assert (inicio, fin) == (hoy.replace(day=1), hoy)


def test_periodo_del_router_respeta_un_rango_valido():
    inicio, fin = agent._periodo_del_router(
        {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"}
    )
    assert (inicio, fin) == (date(2026, 1, 1), date(2026, 1, 31))


def test_aplicar_tope_nunca_deja_pedir_mas_alla_de_hoy():
    hoy = date.today()
    _, fin_real, fue_recortado = agent._aplicar_tope(hoy.replace(day=1), hoy.replace(day=28))
    assert fin_real <= hoy
    if hoy.day < 28:
        assert fue_recortado


# --- _generar_json: timeout y respuesta no interpretable --------------------


class _RespuestaFalsa:
    def __init__(self, texto: str):
        self.text = texto


class _ModelosFalsos:
    def __init__(self, comportamiento):
        self._comportamiento = comportamiento

    async def generate_content(self, **_kwargs):
        return await self._comportamiento()


class _ClienteFalso:
    def __init__(self, comportamiento):
        class _Aio:
            pass

        self.aio = _Aio()
        self.aio.models = _ModelosFalsos(comportamiento)


def test_generar_json_no_se_cuelga_para_siempre_si_la_llamada_no_responde(monkeypatch):
    async def _colgado():
        await asyncio.sleep(10)

    monkeypatch.setattr(agent, "TIMEOUT_GEMINI_SEGUNDOS", 0.05)
    monkeypatch.setattr(agent, "_cliente", lambda: _ClienteFalso(_colgado))

    with pytest.raises(RuntimeError, match="tardó demasiado"):
        asyncio.run(agent._generar_json("prompt", agent.ROUTER_SCHEMA))


def test_generar_json_respuesta_no_json_no_tumba_con_excepcion_cruda(monkeypatch):
    async def _responde_basura():
        return _RespuestaFalsa("esto no es JSON")

    monkeypatch.setattr(agent, "_cliente", lambda: _ClienteFalso(_responde_basura))

    with pytest.raises(agent.RespuestaModeloInvalida):
        asyncio.run(agent._generar_json("prompt", agent.ROUTER_SCHEMA))


def test_clasificar_intencion_cae_en_fuera_de_alcance_si_el_router_no_se_puede_leer(monkeypatch):
    async def _generar_json_roto(_prompt, _schema):
        raise agent.RespuestaModeloInvalida("no se pudo interpretar")

    monkeypatch.setattr(agent, "_generar_json", _generar_json_roto)

    resultado = asyncio.run(agent._clasificar_intencion("¿qué onda?"))
    assert resultado == {"intencion": "fuera_de_alcance"}


def test_decidir_ui_cae_en_fallback_generico_si_no_se_puede_leer(monkeypatch):
    async def _generar_json_roto(_prompt, _schema):
        raise agent.RespuestaModeloInvalida("no se pudo interpretar")

    monkeypatch.setattr(agent, "_generar_json", _generar_json_roto)

    resultado = asyncio.run(agent._decidir_ui([{"label": "Compras", "total": 100.0, "percent": 100.0}]))
    assert resultado["variante"] in {"pie_chart", "bar_chart"}
    assert resultado["mensaje"]


# --- _responder_accion: validación antes de tocar MCP -----------------------


def test_responder_accion_rechaza_accion_no_soportada():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(agent._responder_accion("otra_cosa", {}, "c1"))
    assert exc_info.value.status_code == 400


def test_responder_accion_rechaza_si_falta_categoria():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(agent._responder_accion("crear_limite_gasto", {"monto_limite": 100}, "c1"))
    assert exc_info.value.status_code == 400


def test_responder_accion_rechaza_monto_no_numerico():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            agent._responder_accion(
                "crear_limite_gasto",
                {"categoria": "Compras", "monto_limite": "mucho"},
                "c1",
            )
        )
    assert exc_info.value.status_code == 400


def test_responder_accion_rechaza_monto_no_positivo():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            agent._responder_accion(
                "crear_limite_gasto", {"categoria": "Compras", "monto_limite": 0}, "c1"
            )
        )
    assert exc_info.value.status_code == 400
