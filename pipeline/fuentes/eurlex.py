from __future__ import annotations

import json
from typing import Any, Dict, List

from pipeline.http import get_text
from pipeline.modelos import Item, ResultadoFuente, Ventana


SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"


def obtener(ventana: Ventana, capturado_en: str) -> ResultadoFuente:
    try:
        texto = get_text(
            SPARQL_ENDPOINT,
            params={
                "format": "application/sparql-results+json",
                "query": _query(ventana),
            },
        )
        items = parsear_resultado(json.loads(texto), capturado_en)
    except Exception as exc:
        return ResultadoFuente("EUR-Lex", "degradada", [], str(exc))
    return ResultadoFuente("EUR-Lex", "ok", items)


def parsear_resultado(data: Dict[str, Any], capturado_en: str) -> List[Item]:
    items: List[Item] = []
    vistos = set()
    for binding in data.get("results", {}).get("bindings", []):
        celex = _valor(binding, "celex")
        titulo = _limpiar_titulo(_valor(binding, "title"))
        fecha = _valor(binding, "date")
        if not celex or not titulo or not fecha or celex in vistos:
            continue
        vistos.add(celex)
        items.append(
            Item(
                id=f"celex-{celex}",
                fuente="EUR-Lex",
                tipo=_tipo_eurlex(_valor(binding, "type"), titulo),
                titulo=titulo,
                url=f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}",
                fecha_publicacion=fecha,
                fecha_captura=capturado_en,
                extracto=titulo,
            )
        )
    return items


def _query(ventana: Ventana) -> str:
    return f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?celex ?date ?title ?type WHERE {{
  ?work cdm:resource_legal_id_celex ?celex .
  ?work cdm:work_date_document ?date .
  OPTIONAL {{ ?work cdm:resource_legal_type ?type . }}
  ?exp cdm:expression_belongs_to_work ?work .
  ?exp cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/SPA> .
  ?exp cdm:expression_title ?title .
  FILTER (?date >= "{ventana.desde.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#date> &&
          ?date <= "{ventana.hasta.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#date>)
}}
ORDER BY DESC(?date)
LIMIT 500
""".strip()


def _valor(binding: Dict[str, Any], clave: str) -> str:
    return str(binding.get(clave, {}).get("value", "")).strip()


def _limpiar_titulo(titulo: str) -> str:
    return " ".join(titulo.replace("###", "").split())


def _tipo_eurlex(tipo: str, titulo: str) -> str:
    tipo = tipo.upper()
    texto = titulo.lower()
    if tipo == "R" or "reglamento" in texto:
        return "reglamento"
    if tipo == "L" or "directiva" in texto:
        return "directiva"
    if tipo == "D" or "decisión" in texto or "decision" in texto:
        return "decision"
    if texto.startswith("anuncio") or tipo.startswith("XC"):
        return "anuncio"
    return "otro"
