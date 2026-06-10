from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


TIPOS_VALIDOS = {
    "reglamento",
    "directiva",
    "decision",
    "real_decreto",
    "orden",
    "resolucion",
    "anuncio",
    "opinion_cientifica",
    "otro",
}


@dataclass
class Ventana:
    desde: date
    hasta: date

    def contiene(self, valor: date) -> bool:
        return self.desde <= valor <= self.hasta

    def to_dict(self) -> Dict[str, str]:
        return {"desde": self.desde.isoformat(), "hasta": self.hasta.isoformat()}


@dataclass
class Item:
    id: str
    fuente: str
    tipo: str
    titulo: str
    url: str
    fecha_publicacion: str
    fecha_captura: str
    temas: List[str] = field(default_factory=list)
    terminos: List[str] = field(default_factory=list)
    score: int = 0
    extracto: str = ""

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_VALIDOS:
            self.tipo = "otro"
        if not self.extracto:
            self.extracto = self.titulo

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fuente": self.fuente,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "url": self.url,
            "fecha_publicacion": self.fecha_publicacion,
            "fecha_captura": self.fecha_captura,
            "temas": list(self.temas),
            "terminos": list(self.terminos),
            "score": self.score,
            "extracto": self.extracto,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        return cls(
            id=str(data["id"]),
            fuente=str(data["fuente"]),
            tipo=str(data.get("tipo", "otro")),
            titulo=str(data["titulo"]),
            url=str(data["url"]),
            fecha_publicacion=str(data["fecha_publicacion"]),
            fecha_captura=str(data.get("fecha_captura", "")),
            temas=list(data.get("temas", [])),
            terminos=list(data.get("terminos", [])),
            score=int(data.get("score", 0)),
            extracto=str(data.get("extracto", "")),
        )


@dataclass
class ResultadoFuente:
    fuente: str
    estado: str
    items: List[Item] = field(default_factory=list)
    detalle: Optional[str] = None

    def estado_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"estado": self.estado, "items": len(self.items)}
        if self.detalle:
            data["detalle"] = self.detalle
        return data


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
