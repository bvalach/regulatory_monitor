from __future__ import annotations

from datetime import datetime
from typing import Callable, List

from pipeline.modelos import ResultadoFuente, Ventana


FuenteCallable = Callable[[Ventana, str], ResultadoFuente]


def fecha_iso_desde_aaaammdd(valor: str) -> str:
    return datetime.strptime(valor, "%Y%m%d").date().isoformat()


from . import boe, efsa, eurlex  # noqa: E402


FUENTES: List[FuenteCallable] = [
    boe.obtener,
    eurlex.obtener,
    efsa.obtener,
]


def obtener_todas(ventana: Ventana, capturado_en: str) -> List[ResultadoFuente]:
    return [fuente(ventana, capturado_en) for fuente in FUENTES]
