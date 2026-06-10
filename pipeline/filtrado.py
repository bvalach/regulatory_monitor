from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pipeline.modelos import Item


Termino = Tuple[str, int, str, str]


def filtrar_items(items: Iterable[Item], config: Dict[str, Any]) -> List[Item]:
    filtrados: List[Item] = []
    for item in items:
        evaluado = evaluar_item(item, config)
        if evaluado is not None:
            filtrados.append(evaluado)
    return filtrados


def evaluar_item(item: Item, config: Dict[str, Any]) -> Optional[Item]:
    titulo_norm = normalizar(item.titulo)
    extracto_norm = normalizar(item.extracto)
    texto_norm = f"{titulo_norm} {extracto_norm}"

    for exclusion in config.get("exclusiones", []):
        if _coincide(normalizar(str(exclusion)), texto_norm):
            return None

    score = 0
    temas = set()
    terminos = []

    for termino, peso, tema, etiqueta in _iter_terminos(config):
        termino_norm = normalizar(termino)
        if _coincide(termino_norm, titulo_norm):
            score += peso * 2
            temas.add(tema)
            terminos.append(etiqueta)
        elif _coincide(termino_norm, extracto_norm):
            score += peso
            temas.add(tema)
            terminos.append(etiqueta)

    if score < int(config.get("umbral", 0)):
        return None

    if len(temas) > 1 and "otros" in temas:
        temas.remove("otros")

    return replace(
        item,
        temas=sorted(temas),
        terminos=sorted(set(terminos), key=normalizar),
        score=score,
    )


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    texto = texto.replace("\u00a0", " ")
    return " ".join(texto.split())


def etiquetas_temas(config: Dict[str, Any]) -> Dict[str, str]:
    return {
        tema: str(datos.get("etiqueta", tema))
        for tema, datos in config.get("temas", {}).items()
    }


def _iter_terminos(config: Dict[str, Any]) -> Iterable[Termino]:
    for tema, datos in config.get("temas", {}).items():
        for entrada in datos.get("terminos", []):
            if isinstance(entrada, str):
                yield entrada, 1, tema, entrada
                continue
            termino = str(entrada.get("t", "")).strip()
            peso = int(entrada.get("peso", 1))
            if termino:
                yield termino, peso, tema, termino
            equivalente = str(entrada.get("en", "")).strip()
            if equivalente:
                yield equivalente, peso, tema, equivalente


def _coincide(termino: str, texto: str) -> bool:
    if not termino:
        return False
    if re.search(r"\s", termino):
        return termino in texto
    patron = r"(?<!\w)" + re.escape(termino) + r"(?!\w)"
    return re.search(patron, texto) is not None
