from datetime import date

import pytest

from mcp_server import classification, data
from mcp_server.categorias import CATEGORIAS
from mcp_server.data import Transaccion


@pytest.fixture
def cache_aislada(tmp_path, monkeypatch):
    monkeypatch.setattr(classification, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(classification, "CACHE_PATH", tmp_path / "classification_cache.json")


def test_diccionario_cadena_conocida_match_exacto():
    resultado = classification.clasificar_conceptos(["WALMART"])
    assert resultado["WALMART"] == "Despensa"


def test_diccionario_es_insensible_a_acentos_y_mayusculas():
    resultado = classification.clasificar_conceptos(["cafe rio"])
    assert resultado["cafe rio"] == "Comidas/Restaurantes"


def test_palabra_generica_por_substring_para_negocio_independiente():
    resultado = classification.clasificar_conceptos(["TAQUERIA EL BUEN SABOR"])
    assert resultado["TAQUERIA EL BUEN SABOR"] == "Comidas/Restaurantes"


def test_concepto_desconocido_sin_llm_cae_en_otros(cache_aislada):
    resultado = classification.clasificar_conceptos(["NEGOCIO RARO XYZ"])
    assert resultado["NEGOCIO RARO XYZ"] == "Otros"


def test_llm_resuelve_pendientes_y_los_deja_en_cache(cache_aislada):
    llamadas = []

    def llm_fake(conceptos, categorias):
        llamadas.append(list(conceptos))
        return {c: "Compras" for c in conceptos}

    resultado = classification.clasificar_conceptos(["TIENDA DESCONOCIDA"], llm_fake)
    assert resultado["TIENDA DESCONOCIDA"] == "Compras"
    assert llamadas == [["TIENDA DESCONOCIDA"]]

    # segunda vez, ya no debería llamar al LLM (viene de caché)
    resultado2 = classification.clasificar_conceptos(["TIENDA DESCONOCIDA"], llm_fake)
    assert resultado2["TIENDA DESCONOCIDA"] == "Compras"
    assert len(llamadas) == 1


def test_llm_recibe_pendientes_sin_duplicar(cache_aislada):
    llamadas = []

    def llm_fake(conceptos, categorias):
        llamadas.append(sorted(conceptos))
        return {c: "Compras" for c in conceptos}

    classification.clasificar_conceptos(
        ["TIENDA X", "TIENDA X", "TIENDA X", "TIENDA Y"], llm_fake
    )
    assert llamadas == [["TIENDA X", "TIENDA Y"]]


def test_llm_responde_categoria_invalida_cae_en_otros(cache_aislada):
    def llm_fake(conceptos, categorias):
        return {c: "CategoriaQueNoExiste" for c in conceptos}

    resultado = classification.clasificar_conceptos(["TIENDA DESCONOCIDA"], llm_fake)
    assert resultado["TIENDA DESCONOCIDA"] == "Otros"


def test_llm_no_responde_para_un_concepto_cae_en_otros(cache_aislada):
    def llm_fake(conceptos, categorias):
        return {}

    resultado = classification.clasificar_conceptos(["TIENDA DESCONOCIDA"], llm_fake)
    assert resultado["TIENDA DESCONOCIDA"] == "Otros"


def test_llm_que_lanza_excepcion_cae_en_otros_sin_tumbar_la_consulta(cache_aislada):
    def llm_roto(conceptos, categorias):
        raise RuntimeError("429 Resource exhausted")

    resultado = classification.clasificar_conceptos(
        ["WALMART", "TIENDA DESCONOCIDA"], llm_roto
    )
    assert resultado["WALMART"] == "Despensa"
    assert resultado["TIENDA DESCONOCIDA"] == "Otros"


def test_llm_que_lanza_excepcion_no_cachea_para_poder_reintentar_despues(cache_aislada):
    llamadas = []

    def llm_intermitente(conceptos, categorias):
        llamadas.append(list(conceptos))
        if len(llamadas) == 1:
            raise RuntimeError("429 Resource exhausted")
        return {c: "Compras" for c in conceptos}

    primera = classification.clasificar_conceptos(["TIENDA DESCONOCIDA"], llm_intermitente)
    assert primera["TIENDA DESCONOCIDA"] == "Otros"

    segunda = classification.clasificar_conceptos(["TIENDA DESCONOCIDA"], llm_intermitente)
    assert segunda["TIENDA DESCONOCIDA"] == "Compras"
    assert len(llamadas) == 2


def test_cache_corrupta_no_tumba_y_se_trata_como_vacia(cache_aislada):
    classification.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    classification.CACHE_PATH.write_text("{esto no es json valido", encoding="utf-8")

    # No debe lanzar -- una caché corrupta solo significa volver a preguntar
    # al LLM lo que ya se sabía, no tumbar la consulta.
    resultado = classification.clasificar_conceptos(["WALMART"])
    assert resultado["WALMART"] == "Despensa"


def test_categorias_pasadas_al_llm_son_las_8_validas(cache_aislada):
    categorias_recibidas = {}

    def llm_fake(conceptos, categorias):
        categorias_recibidas["valor"] = categorias
        return {}

    classification.clasificar_conceptos(["X"], llm_fake)
    assert categorias_recibidas["valor"] == CATEGORIAS


def test_obtener_gasto_por_categoria_excluye_movimientos_no_gasto(monkeypatch, cache_aislada):
    transacciones = [
        Transaccion(date(2026, 1, 1), "WALMART", 500.0, "compra"),
        Transaccion(date(2026, 1, 2), "RETIRO CAJERO", 1000.0, "retiro"),
        Transaccion(date(2026, 1, 3), "TRANSFERENCIA SPEI", 2000.0, "transferencia"),
    ]
    monkeypatch.setattr(data, "obtener_transacciones", lambda *_: transacciones)

    resultado = classification.obtener_gasto_por_categoria(date(2026, 1, 1), date(2026, 1, 3))

    assert "Otros" not in resultado
    assert set(resultado.keys()) == {"Despensa"}
    assert resultado["Despensa"]["monto_total"] == 500.0


def test_obtener_gasto_por_categoria_agrega_monto_total_y_anida_transacciones(
    monkeypatch, cache_aislada
):
    transacciones = [
        Transaccion(date(2026, 1, 1), "WALMART", 500.0, "compra"),
        Transaccion(date(2026, 1, 2), "SORIANA", 300.0, "compra"),
        Transaccion(date(2026, 1, 3), "STARBUCKS", 80.0, "compra"),
    ]
    monkeypatch.setattr(data, "obtener_transacciones", lambda *_: transacciones)

    resultado = classification.obtener_gasto_por_categoria(date(2026, 1, 1), date(2026, 1, 3))

    assert resultado["Despensa"]["monto_total"] == 800.0
    assert len(resultado["Despensa"]["transacciones"]) == 2
    assert resultado["Comidas/Restaurantes"]["monto_total"] == 80.0
    assert resultado["Comidas/Restaurantes"]["transacciones"] == [
        {"fecha": "2026-01-03", "comercio": "STARBUCKS", "monto": 80.0}
    ]
