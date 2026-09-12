"""Categorías válidas y tipos de movimiento excluidos del desglose de gasto.

Vive en su propio módulo (en vez de en `data.py` o `classification.py`) porque
ambos lo necesitan: `data.py` valida contra `CATEGORIAS` al crear un límite de
gasto, y `classification.py` usa `TIPOS_NO_GASTO` para excluir movimientos que
no son gasto antes de clasificar. Ponerlo en cualquiera de los dos dos
módulos crearía un import circular.
"""

CATEGORIAS = [
    "Despensa",
    "Comidas/Restaurantes",
    "Servicios",
    "Transporte",
    "Entretenimiento/Suscripciones",
    "Salud",
    "Compras",
    "Otros",
]

# Movimientos que no son gasto discrecional: se excluyen del desglose por
# categoría desde el inicio, no cuentan como "Otros" (ver CLAUDE.md, sección 3).
TIPOS_NO_GASTO = {"retiro", "transferencia", "deposito", "comision"}
