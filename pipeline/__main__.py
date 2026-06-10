from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

from pipeline import fuentes
from pipeline.almacen import fusionar_y_guardar
from pipeline.config import cargar_config
from pipeline.digest import generar_salidas, ultima_semana_iso_completa
from pipeline.filtrado import filtrar_items
from pipeline.modelos import Ventana, utc_now_iso


ROOT = Path(__file__).resolve().parents[1]


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    config = cargar_config(args.config)
    hoy = _parse_date(args.hoy) if args.hoy else date.today()
    ventana = _calcular_ventana(args, config, hoy)
    capturado_en = utc_now_iso()

    resultados = fuentes.obtener_todas(ventana, capturado_en)
    items_brutos = [item for resultado in resultados for item in resultado.items]
    items_filtrados = filtrar_items(items_brutos, config)
    items, nuevos = fusionar_y_guardar(args.data_dir, items_filtrados)
    digest_objetivo = ultima_semana_iso_completa(hoy)

    generar_salidas(
        data_dir=args.data_dir,
        digest_md_dir=args.digest_md_dir,
        items=items,
        config=config,
        fuentes=resultados,
        generado_en=capturado_en,
        ventana=ventana,
        digest_objetivo=digest_objetivo,
        items_nuevos=nuevos,
    )

    degradadas = [r for r in resultados if r.estado != "ok"]
    print(
        f"Ventana {ventana.desde}..{ventana.hasta}: "
        f"{len(items_brutos)} brutos, {len(items_filtrados)} relevantes, {nuevos} nuevos."
    )
    if degradadas:
        print("Fuentes degradadas: " + ", ".join(r.fuente for r in degradadas))

    if resultados and all(r.estado != "ok" for r in resultados):
        return 1
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera el observatorio regulatorio.")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "terminos.yaml")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "docs" / "data")
    parser.add_argument("--digest-md-dir", type=Path, default=ROOT / "digests")
    parser.add_argument("--desde", help="Fecha inicial de la ventana, en formato AAAA-MM-DD.")
    parser.add_argument("--hasta", help="Fecha final de la ventana, en formato AAAA-MM-DD.")
    parser.add_argument("--hoy", help="Fecha de referencia para pruebas/backfill, en formato AAAA-MM-DD.")
    parser.add_argument("--ventana-dias", type=int, help="Días de solape a consultar.")
    return parser.parse_args(argv)


def _calcular_ventana(args: argparse.Namespace, config: dict, hoy: date) -> Ventana:
    hasta = _parse_date(args.hasta) if args.hasta else hoy
    if args.desde:
        desde = _parse_date(args.desde)
    else:
        dias = args.ventana_dias or int(config.get("ventana_dias", 9))
        desde = hasta - timedelta(days=dias)
    return Ventana(desde=desde, hasta=hasta)


def _parse_date(valor: str) -> date:
    return datetime.strptime(valor, "%Y-%m-%d").date()


if __name__ == "__main__":
    sys.exit(main())
