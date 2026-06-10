from pipeline.filtrado import evaluar_item, normalizar
from pipeline.modelos import Item


CONFIG = {
    "umbral": 8,
    "temas": {
        "aditivos_contaminantes": {
            "etiqueta": "Aditivos y contaminantes",
            "terminos": [{"t": "nitritos", "peso": 10, "en": "nitrites"}],
        },
        "higiene_seguridad": {
            "etiqueta": "Higiene",
            "terminos": [{"t": "productos cárnicos", "peso": 9, "en": "meat products"}],
        },
    },
    "exclusiones": ["nombramiento"],
}


def item(titulo, extracto=""):
    return Item(
        id="x",
        fuente="BOE",
        tipo="otro",
        titulo=titulo,
        url="https://example.test",
        fecha_publicacion="2026-06-03",
        fecha_captura="2026-06-10T08:00:00Z",
        extracto=extracto or titulo,
    )


def test_normaliza_minusculas_y_tildes():
    assert normalizar("Productos CÁRNICOS") == "productos carnicos"


def test_titulo_pondera_por_dos_y_asigna_temas():
    evaluado = evaluar_item(item("Reglamento sobre nitritos en productos cárnicos"), CONFIG)

    assert evaluado is not None
    assert evaluado.score == 38
    assert evaluado.temas == ["aditivos_contaminantes", "higiene_seguridad"]
    assert evaluado.terminos == ["nitritos", "productos cárnicos"]


def test_equivalente_ingles_en_extracto():
    evaluado = evaluar_item(item("EFSA opinion", "Risk assessment on nitrites in meat products."), CONFIG)

    assert evaluado is not None
    assert evaluado.score == 19


def test_exclusion_absoluta_descarta():
    assert evaluar_item(item("Resolución de nombramiento sobre productos cárnicos"), CONFIG) is None
