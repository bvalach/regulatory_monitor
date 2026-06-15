from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Iterable, List

from pipeline.http import get_json
from pipeline.modelos import Item, ResultadoFuente, Ventana

from . import fecha_iso_desde_aaaammdd


URL_SUMARIO = "https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}"
TIMEOUT_SEGUNDOS = 12
REINTENTOS = 1
MAX_ERRORES_CONSECUTIVOS = 3


def obtener(ventana: Ventana, capturado_en: str) -> ResultadoFuente:
    items: List[Item] = []
    errores: List[str] = []
    errores_consecutivos = 0
    dia = ventana.desde
    while dia <= ventana.hasta:
        fecha = dia.strftime("%Y%m%d")
        try:
            data = get_json(
                URL_SUMARIO.format(fecha=fecha),
                headers={"Accept": "application/json"},
                timeout=TIMEOUT_SEGUNDOS,
                retries=REINTENTOS,
            )
            items.extend(parsear_sumario(data, capturado_en))
            errores_consecutivos = 0
        except Exception as exc:
            if "HTTP Error 404" not in str(exc):
                errores.append(f"{fecha}: {exc}")
                errores_consecutivos += 1
                if errores_consecutivos >= MAX_ERRORES_CONSECUTIVOS:
                    errores.append(
                        f"consulta abortada tras {MAX_ERRORES_CONSECUTIVOS} errores consecutivos"
                    )
                    break
            else:
                errores_consecutivos = 0
        dia += timedelta(days=1)

    if errores:
        return ResultadoFuente("BOE", "degradada", items, "; ".join(errores[:4]))
    return ResultadoFuente("BOE", "ok", items)


def parsear_sumario(data: Dict[str, Any], capturado_en: str) -> List[Item]:
    sumario = data.get("data", {}).get("sumario", {})
    fecha_raw = sumario.get("metadatos", {}).get("fecha_publicacion", "")
    if not fecha_raw:
        return []
    fecha_publicacion = fecha_iso_desde_aaaammdd(fecha_raw)

    items: List[Item] = []
    for nodo in _iter_items(sumario):
        identificador = str(nodo.get("identificador", "")).strip()
        titulo = _limpiar(str(nodo.get("titulo", "")).strip())
        if not identificador or not titulo:
            continue
        url = str(nodo.get("url_html") or nodo.get("url_xml") or "")
        items.append(
            Item(
                id=f"boe-{identificador}",
                fuente="BOE",
                tipo=_tipo_boe(titulo, identificador),
                titulo=titulo,
                url=url,
                fecha_publicacion=fecha_publicacion,
                fecha_captura=capturado_en,
                extracto=titulo,
            )
        )
    return items


def _iter_items(nodo: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(nodo, dict):
        if "identificador" in nodo and "titulo" in nodo:
            yield nodo
        for valor in nodo.values():
            yield from _iter_items(valor)
    elif isinstance(nodo, list):
        for valor in nodo:
            yield from _iter_items(valor)


def _tipo_boe(titulo: str, identificador: str) -> str:
    texto = titulo.lower()
    if texto.startswith("real decreto"):
        return "real_decreto"
    if texto.startswith("orden"):
        return "orden"
    if texto.startswith("resolución") or texto.startswith("resolucion"):
        return "resolucion"
    if texto.startswith("anuncio") or identificador.startswith("BOE-B"):
        return "anuncio"
    return "otro"


def _limpiar(texto: str) -> str:
    return " ".join(texto.split())
