from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def cargar_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if "temas" not in data or not isinstance(data["temas"], dict):
        raise ValueError("config/terminos.yaml debe definir un mapa 'temas'.")
    if "umbral" not in data:
        raise ValueError("config/terminos.yaml debe definir 'umbral'.")

    data.setdefault("ventana_dias", 9)
    data.setdefault("exclusiones", [])
    return data
