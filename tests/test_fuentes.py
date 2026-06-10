import json
from datetime import date
from pathlib import Path

from pipeline.fuentes.boe import parsear_sumario
from pipeline.fuentes.efsa import parsear_rss
from pipeline.fuentes.eurlex import parsear_resultado
from pipeline.modelos import Ventana


FIXTURES = Path(__file__).parent / "fixtures"


def test_parsea_boe_con_objetos_y_listas():
    data = json.loads((FIXTURES / "boe" / "sumario.json").read_text(encoding="utf-8"))

    items = parsear_sumario(data, "2026-06-10T08:00:00Z")

    assert len(items) == 2
    assert items[0].id == "boe-BOE-A-2026-01234"
    assert items[0].tipo == "real_decreto"
    assert items[0].fecha_publicacion == "2026-06-03"


def test_parsea_eurlex_y_limpia_titulo():
    data = json.loads((FIXTURES / "eurlex" / "resultado.json").read_text(encoding="utf-8"))

    items = parsear_resultado(data, "2026-06-10T08:00:00Z")

    assert len(items) == 1
    assert items[0].id == "celex-32026R0123"
    assert items[0].tipo == "reglamento"
    assert not items[0].titulo.endswith("###")


def test_parsea_efsa_rss_filtrando_por_ventana():
    xml = (FIXTURES / "efsa" / "publications.xml").read_text(encoding="utf-8")
    ventana = Ventana(date(2026, 6, 1), date(2026, 6, 7))

    items = parsear_rss(xml, ventana, "2026-06-10T08:00:00Z")

    assert len(items) == 1
    assert items[0].fuente == "EFSA"
    assert items[0].tipo == "opinion_cientifica"
    assert "10.2903" in items[0].id
    assert "<p>" not in items[0].extracto
