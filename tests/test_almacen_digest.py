import json
from datetime import date

from pipeline.almacen import fusionar_y_guardar
from pipeline.digest import generar_salidas, ultima_semana_iso_completa
from pipeline.modelos import Item, ResultadoFuente, Ventana


def test_fusiona_sin_duplicar_y_preserva_fecha_captura(tmp_path):
    data_dir = tmp_path / "docs" / "data"
    original = _item("2026-06-03", captura="2026-06-10T08:00:00Z")
    repetido = _item("2026-06-03", captura="2026-06-11T08:00:00Z", score=30)

    _, nuevos_1 = fusionar_y_guardar(data_dir, [original])
    items, nuevos_2 = fusionar_y_guardar(data_dir, [repetido])

    assert nuevos_1 == 1
    assert nuevos_2 == 0
    assert len(items) == 1
    assert items[0].fecha_captura == "2026-06-10T08:00:00Z"
    assert items[0].score == 30


def test_genera_contratos_digest_y_meta(tmp_path):
    data_dir = tmp_path / "docs" / "data"
    md_dir = tmp_path / "digests"
    items, _ = fusionar_y_guardar(data_dir, [_item("2026-06-03")])
    config = {
        "temas": {
            "aditivos_contaminantes": {"etiqueta": "Aditivos y contaminantes", "terminos": []}
        }
    }

    generar_salidas(
        data_dir=data_dir,
        digest_md_dir=md_dir,
        items=items,
        config=config,
        fuentes=[ResultadoFuente("BOE", "ok", items)],
        generado_en="2026-06-10T08:00:00Z",
        ventana=Ventana(date(2026, 6, 1), date(2026, 6, 10)),
        digest_objetivo="2026-W23",
        items_nuevos=1,
    )

    digest = json.loads((data_dir / "digests" / "2026-W23.json").read_text(encoding="utf-8"))
    indice = json.loads((data_dir / "digests" / "index.json").read_text(encoding="utf-8"))
    meta = json.loads((data_dir / "meta.json").read_text(encoding="utf-8"))

    assert digest["sin_novedades"] is False
    assert digest["temas"][0]["items"][0]["id"] == "item-2026-06-03"
    assert indice["ultimo"] == "2026-W23"
    assert meta["digest_reciente"] == "2026-W23"
    assert (md_dir / "2026-W23.md").exists()


def test_genera_digest_con_fuente_degradada(tmp_path):
    data_dir = tmp_path / "docs" / "data"
    md_dir = tmp_path / "digests"
    items, _ = fusionar_y_guardar(data_dir, [_item("2026-06-03")])
    config = {
        "temas": {
            "aditivos_contaminantes": {"etiqueta": "Aditivos y contaminantes", "terminos": []}
        }
    }

    generar_salidas(
        data_dir=data_dir,
        digest_md_dir=md_dir,
        items=items,
        config=config,
        fuentes=[
            ResultadoFuente("BOE", "ok", items),
            ResultadoFuente("EFSA", "degradada", [], "timeout"),
        ],
        generado_en="2026-06-10T08:00:00Z",
        ventana=Ventana(date(2026, 6, 1), date(2026, 6, 10)),
        digest_objetivo="2026-W23",
        items_nuevos=1,
    )

    meta = json.loads((data_dir / "meta.json").read_text(encoding="utf-8"))
    digest = json.loads((data_dir / "digests" / "2026-W23.json").read_text(encoding="utf-8"))

    assert meta["fuentes"]["EFSA"]["estado"] == "degradada"
    assert meta["fuentes"]["EFSA"]["detalle"] == "timeout"
    assert digest["estado_fuentes"]["EFSA"]["estado"] == "degradada"


def test_ultima_semana_iso_completa():
    assert ultima_semana_iso_completa(date(2026, 6, 10)) == "2026-W23"


def _item(fecha, captura="2026-06-10T08:00:00Z", score=20):
    return Item(
        id=f"item-{fecha}",
        fuente="BOE",
        tipo="reglamento",
        titulo="Reglamento sobre nitritos en productos cárnicos",
        url="https://example.test",
        fecha_publicacion=fecha,
        fecha_captura=captura,
        temas=["aditivos_contaminantes"],
        terminos=["nitritos"],
        score=score,
        extracto="Extracto oficial",
    )
