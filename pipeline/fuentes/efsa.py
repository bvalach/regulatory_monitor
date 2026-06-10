from __future__ import annotations

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from xml.etree import ElementTree as ET

from pipeline.http import get_text
from pipeline.modelos import Item, ResultadoFuente, Ventana


RSS_PUBLICACIONES = "https://www.efsa.europa.eu/en/publications/rss"


def obtener(ventana: Ventana, capturado_en: str) -> ResultadoFuente:
    try:
        xml = get_text(RSS_PUBLICACIONES, headers={"Accept": "application/rss+xml, application/xml"})
        items = parsear_rss(xml, ventana, capturado_en)
    except Exception as exc:
        return ResultadoFuente("EFSA", "degradada", [], str(exc))
    return ResultadoFuente("EFSA", "ok", items)


def parsear_rss(xml: str, ventana: Ventana, capturado_en: str) -> List[Item]:
    root = ET.fromstring(xml)
    items: List[Item] = []
    for nodo in root.findall(".//item"):
        titulo = _texto(nodo, "title")
        url = _texto(nodo, "link")
        descripcion = _limpiar_html(_texto(nodo, "description"))
        fecha = _fecha_rss(_texto(nodo, "pubDate"))
        if not fecha or not ventana.contiene(fecha.date()):
            continue
        identificador = _identificador(url, _texto(nodo, "guid"))
        items.append(
            Item(
                id=f"efsa-{identificador}",
                fuente="EFSA",
                tipo="opinion_cientifica",
                titulo=titulo,
                url=url,
                fecha_publicacion=fecha.date().isoformat(),
                fecha_captura=capturado_en,
                extracto=descripcion or titulo,
            )
        )
    return items


def _texto(nodo: ET.Element, tag: str) -> str:
    hijo = nodo.find(tag)
    return "" if hijo is None or hijo.text is None else hijo.text.strip()


def _fecha_rss(valor: str) -> Optional[datetime]:
    if not valor:
        return None
    parsed = parsedate_to_datetime(valor)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _identificador(url: str, guid: str) -> str:
    doi = re.search(r"10\.\d{4,9}/[^\s?#]+", url)
    if doi:
        return doi.group(0).rstrip("/").replace("/", "_")
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", guid or url).strip("-")


def _limpiar_html(texto: str) -> str:
    texto = html.unescape(texto)
    texto = re.sub(r"<[^>]+>", " ", texto)
    return " ".join(texto.split())
