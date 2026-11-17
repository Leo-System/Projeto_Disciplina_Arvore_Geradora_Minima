"""Carregamento dos dados processados usados pela aplicação.

O sistema em execução lê **apenas** ``data/processed/``. A preparação dos
arquivos brutos é feita por ``scripts/build_dataset.py`` (fora da execução).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .algorithms.graph import Graph

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CITIES_FILE = PROCESSED_DIR / "cities.csv"
EDGES_FILE = PROCESSED_DIR / "edges.csv"


class DataLoadError(RuntimeError):
    """Erro ao ler os dados processados."""


@dataclass(frozen=True)
class CityRecord:
    id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class EdgeRecord:
    u: str
    v: str
    dist_km: float
    border_km: float | None
    source: str
    short_border: bool


@lru_cache(maxsize=1)
def load_cities() -> tuple[CityRecord, ...]:
    """Lê ``data/processed/cities.csv`` uma única vez por processo."""
    if not CITIES_FILE.exists():
        raise DataLoadError(
            f"Arquivo de dados não encontrado: {CITIES_FILE}. "
            "Execute 'python scripts/build_dataset.py' para gerá-lo."
        )
    cities: list[CityRecord] = []
    with CITIES_FILE.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"id", "name", "lat", "lon"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise DataLoadError(f"Colunas ausentes em {CITIES_FILE.name}: {sorted(missing)}")
        for line_number, row in enumerate(reader, start=2):
            try:
                cities.append(
                    CityRecord(
                        id=row["id"].strip(),
                        name=row["name"].strip(),
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise DataLoadError(
                    f"Linha inválida em {CITIES_FILE.name}, linha {line_number}: {row}"
                ) from exc
    if not cities:
        raise DataLoadError("Nenhum município encontrado nos dados processados.")
    return tuple(cities)


@lru_cache(maxsize=1)
def load_edges() -> tuple[EdgeRecord, ...]:
    """Lê ``data/processed/edges.csv`` uma única vez por processo."""
    if not EDGES_FILE.exists():
        raise DataLoadError(
            f"Arquivo de dados não encontrado: {EDGES_FILE}. "
            "Execute 'python scripts/build_dataset.py' para gerá-lo."
        )
    edges: list[EdgeRecord] = []
    with EDGES_FILE.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"u", "v", "dist_km", "border_km", "source", "short_border"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise DataLoadError(f"Colunas ausentes em {EDGES_FILE.name}: {sorted(missing)}")
        for line_number, row in enumerate(reader, start=2):
            try:
                border_raw = (row["border_km"] or "").strip()
                edges.append(
                    EdgeRecord(
                        u=row["u"].strip(),
                        v=row["v"].strip(),
                        dist_km=float(row["dist_km"]),
                        border_km=float(border_raw) if border_raw else None,
                        source=row["source"].strip(),
                        short_border=row["short_border"].strip().lower() == "true",
                    )
                )
            except (TypeError, ValueError) as exc:
                raise DataLoadError(
                    f"Linha inválida em {EDGES_FILE.name}, linha {line_number}: {row}"
                ) from exc
    if not edges:
        raise DataLoadError("Nenhuma aresta encontrada nos dados processados.")
    return tuple(edges)


@lru_cache(maxsize=2)
def load_graph(include_manual: bool = True) -> Graph:
    """Monta o grafo completo do estado, opcionalmente com ligações manuais."""
    nodes = [
        {"id": city.id, "name": city.name, "lat": city.lat, "lon": city.lon}
        for city in load_cities()
    ]
    edge_payload = [
        {
            "u": edge.u,
            "v": edge.v,
            "weight": edge.dist_km,
            "attrs": {
                "border_km": edge.border_km,
                "source": edge.source,
                "short_border": edge.short_border,
            },
        }
        for edge in load_edges()
        if include_manual or edge.source != "manual"
    ]
    return Graph.from_records(nodes, edge_payload)


def city_by_id(city_id: str) -> CityRecord:
    """Busca um município pelo código IBGE."""
    for city in load_cities():
        if city.id == city_id:
            return city
    raise DataLoadError(f"Município não encontrado: {city_id}")


def city_name_map() -> dict[str, str]:
    """Mapeamento código IBGE -> nome exibido."""
    return {city.id: city.name for city in load_cities()}
