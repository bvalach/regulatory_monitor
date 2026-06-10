from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from pipeline.almacen import anios_disponibles
from pipeline.filtrado import etiquetas_temas
from pipeline.modelos import Item, ResultadoFuente, Ventana


def ultima_semana_iso_completa(hoy: date) -> str:
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    lunes_objetivo = lunes_actual - timedelta(days=7)
    iso = lunes_objetivo.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def semana_iso(fecha: date) -> str:
    iso = fecha.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def rango_semana(semana_id: str) -> Ventana:
    anio, semana = semana_id.split("-W")
    lunes = datetime.strptime(f"{anio} {semana} 1", "%G %V %u").date()
    return Ventana(lunes, lunes + timedelta(days=6))


def generar_salidas(
    *,
    data_dir: Path,
    digest_md_dir: Path,
    items: List[Item],
    config: Dict[str, Any],
    fuentes: List[ResultadoFuente],
    generado_en: str,
    ventana: Ventana,
    digest_objetivo: str,
    items_nuevos: int,
) -> None:
    semanas = {digest_objetivo}
    semanas.update(semana for semana in _semanas_de_items(items) if semana <= digest_objetivo)

    for semana_id in sorted(semanas):
        generar_digest_semana(
            semana_id=semana_id,
            data_dir=data_dir,
            digest_md_dir=digest_md_dir,
            items=items,
            config=config,
            fuentes=fuentes,
            generado_en=generado_en,
        )

    indice = actualizar_indice_digests(data_dir)
    meta = {
        "ultima_ejecucion": generado_en,
        "ventana_consulta": ventana.to_dict(),
        "digest_reciente": digest_objetivo,
        "anios_disponibles": anios_disponibles(data_dir),
        "recuentos": {"items_total": len(items), "items_nuevos": items_nuevos},
        "fuentes": {resultado.fuente: resultado.estado_dict() for resultado in fuentes},
    }
    _escribir_json(data_dir / "meta.json", meta)

    if not indice.get("ultimo"):
        actualizar_indice_digests(data_dir)


def generar_digest_semana(
    *,
    semana_id: str,
    data_dir: Path,
    digest_md_dir: Path,
    items: List[Item],
    config: Dict[str, Any],
    fuentes: List[ResultadoFuente],
    generado_en: str,
) -> Dict[str, Any]:
    rango = rango_semana(semana_id)
    etiquetas = etiquetas_temas(config)
    items_semana = [
        item
        for item in items
        if rango.contiene(datetime.strptime(item.fecha_publicacion, "%Y-%m-%d").date())
    ]

    temas = []
    for tema_id, etiqueta in etiquetas.items():
        items_tema = [item for item in items_semana if tema_id in item.temas]
        if items_tema:
            temas.append(
                {
                    "id": tema_id,
                    "etiqueta": etiqueta,
                    "items": [item.to_dict() for item in sorted(items_tema, key=_orden_digest, reverse=True)],
                }
            )

    data = {
        "id": semana_id,
        "desde": rango.desde.isoformat(),
        "hasta": rango.hasta.isoformat(),
        "generado_en": generado_en,
        "estado_fuentes": {resultado.fuente: resultado.estado_dict() for resultado in fuentes},
        "sin_novedades": len(items_semana) == 0,
        "temas": temas,
    }
    _escribir_json(data_dir / "digests" / f"{semana_id}.json", data)
    _escribir_markdown(digest_md_dir / f"{semana_id}.md", data)
    return data


def actualizar_indice_digests(data_dir: Path) -> Dict[str, Any]:
    digests_dir = data_dir / "digests"
    entradas = []
    for path in sorted(digests_dir.glob("*.json"), reverse=True):
        if path.name == "index.json":
            continue
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        entradas.append(
            {
                "id": data["id"],
                "desde": data["desde"],
                "hasta": data["hasta"],
                "json": f"data/digests/{data['id']}.json",
                "markdown_repo_path": f"digests/{data['id']}.md",
                "items": sum(len(tema["items"]) for tema in data.get("temas", [])),
            }
        )
    indice = {"ultimo": entradas[0]["id"] if entradas else None, "digests": entradas}
    _escribir_json(digests_dir / "index.json", indice)
    return indice


def _semanas_de_items(items: Iterable[Item]) -> Set[str]:
    semanas = set()
    for item in items:
        fecha = datetime.strptime(item.fecha_publicacion, "%Y-%m-%d").date()
        semanas.add(semana_iso(fecha))
    return semanas


def _orden_digest(item: Item) -> tuple:
    return (item.fecha_publicacion, item.score, item.titulo.lower())


def _escribir_markdown(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# Digest regulatorio {data['id']}",
        "",
        f"Periodo: {data['desde']} a {data['hasta']}",
        f"Generado: {data['generado_en']}",
        "",
    ]
    degradadas = [
        f"{fuente}: {estado.get('detalle', 'degradada')}"
        for fuente, estado in data["estado_fuentes"].items()
        if estado.get("estado") != "ok"
    ]
    if degradadas:
        lineas.extend(["## Avisos de fuentes", "", *[f"- {aviso}" for aviso in degradadas], ""])

    if data["sin_novedades"]:
        lineas.extend(["No se han detectado novedades relevantes esta semana.", ""])
    else:
        for tema in data["temas"]:
            lineas.extend([f"## {tema['etiqueta']}", ""])
            for item in tema["items"]:
                lineas.extend(
                    [
                        f"- [{item['titulo']}]({item['url']})",
                        f"  - Fuente: {item['fuente']} · Tipo: {item['tipo']} · Fecha: {item['fecha_publicacion']} · Score: {item['score']}",
                        f"  - Extracto oficial: {item['extracto']}",
                    ]
                )
            lineas.append("")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lineas).rstrip() + "\n")


def _escribir_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
