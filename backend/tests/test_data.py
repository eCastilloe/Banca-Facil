from datetime import date, timedelta

import pytest

from mcp_server import data


def test_obtener_transacciones_respeta_el_rango():
    inicio = date(2026, 1, 1)
    fin = date(2026, 1, 5)
    transacciones = data.obtener_transacciones(inicio, fin)
    assert all(inicio <= t.fecha <= fin for t in transacciones)


def test_obtener_transacciones_es_deterministico():
    inicio, fin = date(2026, 1, 1), date(2026, 2, 1)
    primera = data.obtener_transacciones(inicio, fin)
    segunda = data.obtener_transacciones(inicio, fin)
    assert primera == segunda


def test_obtener_transacciones_dia_mas_reciente_es_estable_sin_importar_hoy():
    dia = date(2026, 1, 15)
    a = data.obtener_transacciones(dia, dia)
    b = data.obtener_transacciones(dia, dia + timedelta(days=10))
    dia_en_b = [t for t in b if t.fecha == dia]
    assert a == dia_en_b


def test_obtener_transacciones_fecha_fin_antes_de_inicio_lanza_error():
    with pytest.raises(ValueError):
        data.obtener_transacciones(date(2026, 2, 1), date(2026, 1, 1))


def test_obtener_transacciones_incluye_tipos_no_gasto():
    # data.py no filtra: la exclusión de no-gasto vive en classification.py.
    inicio, fin = date(2026, 1, 1), date(2026, 3, 1)
    tipos = {t.tipo_movimiento for t in data.obtener_transacciones(inicio, fin)}
    assert tipos - {"compra"}


@pytest.fixture
def limites_aislados(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(data, "LIMITES_PATH", tmp_path / "limites_gasto.json")


def test_crear_limite_gasto_guarda_y_se_puede_leer(limites_aislados):
    resultado = data.crear_limite_gasto("Despensa", 3000.0)
    assert resultado["ok"] is True
    assert resultado["limite"]["categoria"] == "Despensa"
    assert resultado["limite"]["monto_limite"] == 3000.0
    assert "creado_en" in resultado["limite"]

    limites = data.obtener_limites_gasto()
    assert len(limites) == 1
    assert limites[0]["categoria"] == "Despensa"


def test_crear_limite_gasto_reemplaza_el_limite_anterior_de_la_misma_categoria(limites_aislados):
    data.crear_limite_gasto("Despensa", 3000.0)
    data.crear_limite_gasto("Despensa", 2500.0)

    limites = data.obtener_limites_gasto()
    assert len(limites) == 1
    assert limites[0]["monto_limite"] == 2500.0


def test_crear_limite_gasto_categoria_invalida_lanza_error(limites_aislados):
    with pytest.raises(ValueError):
        data.crear_limite_gasto("CategoriaInventada", 100.0)


def test_crear_limite_gasto_monto_no_positivo_lanza_error(limites_aislados):
    with pytest.raises(ValueError):
        data.crear_limite_gasto("Despensa", 0)


def test_crear_limite_gasto_no_deja_archivo_temporal_tras_guardar(limites_aislados):
    data.crear_limite_gasto("Despensa", 3000.0)
    # La escritura es atómica (tmp + os.replace): no debe quedar basura.
    assert list(data.STORAGE_DIR.glob("*.tmp")) == []


def test_leer_limites_con_json_corrupto_no_tumba_y_regresa_vacio(limites_aislados):
    data.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    data.LIMITES_PATH.write_text("{esto no es json valido", encoding="utf-8")

    assert data.obtener_limites_gasto() == []


def test_eliminar_limite_gasto_quita_solo_la_categoria_pedida(limites_aislados):
    data.crear_limite_gasto("Despensa", 3000.0)
    data.crear_limite_gasto("Compras", 2000.0)

    resultado = data.eliminar_limite_gasto("Despensa")

    assert resultado == {"ok": True, "categoria": "Despensa", "existia": True}
    limites = data.obtener_limites_gasto()
    assert len(limites) == 1
    assert limites[0]["categoria"] == "Compras"


def test_eliminar_limite_gasto_categoria_sin_limite_no_es_error(limites_aislados):
    resultado = data.eliminar_limite_gasto("Salud")
    assert resultado == {"ok": True, "categoria": "Salud", "existia": False}
    assert data.obtener_limites_gasto() == []
