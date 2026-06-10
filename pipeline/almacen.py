from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from pipeline.modelos import Item


def cargar_items(data_dir: Path) -> List[Item]:
    items: List[Item] = []
    for path in sorted(data_dir.glob("items-*.json")):
        if path.name == "items-index.json":
            continue
        with path.open("r", encoding="utf-8") as handle:
            items.extend(Item.from_dict(row) for row in json.load(handle))
    return items


def fusionar_y_guardar(data_dir: Path, nuevos: Iterable[Item]) -> Tuple[List[Item], int]:
    data_dir.mkdir(parents=True, exist_ok=True)
    existentes = {item.id: item for item in cargar_items(data_dir)}
    nuevos_count = 0

    for item in nuevos:
        if item.id in existentes:
            previo = existentes[item.id]
            item.fecha_captura = previo.fecha_captura
        else:
            nuevos_count += 1
        existentes[item.id] = item

    todos = sorted(existentes.values(), key=_orden_item, reverse=True)
    por_anio: Dict[int, List[Item]] = {}
    for item in todos:
        por_anio.setdefault(int(item.fecha_publicacion[:4]), []).append(item)

    for anio, items in por_anio.items():
        _escribir_json(data_dir / f"items-{anio}.json", [item.to_dict() for item in items])

    _actualizar_indice(data_dir, por_anio)
    return todos, nuevos_count


def anios_disponibles(data_dir: Path) -> List[int]:
    anios: Set[int] = set()
    for path in data_dir.glob("items-*.json"):
        if path.name == "items-index.json":
            continue
        try:
            anios.add(int(path.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return sorted(anios, reverse=True)


def _actualizar_indice(data_dir: Path, por_anio: Dict[int, List[Item]]) -> None:
    entradas = []
    for anio in sorted(por_anio.keys(), reverse=True):
        entradas.append(
            {
                "anio": anio,
                "path": f"data/items-{anio}.json",
                "items": len(por_anio[anio]),
            }
        )
    _escribir_json(data_dir / "items-index.json", {"anios": entradas})


def _orden_item(item: Item) -> tuple:
    return (item.fecha_publicacion, item.score, item.titulo.lower())


def _escribir_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
