"""Instâncias prontas (presets), geradas por regra a partir dos dados reais.

Nenhuma lista de cidades é escrita "de memória": os presets usam busca por
nome ou vizinhança no próprio grafo carregado de ``data/processed/``.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from ..algorithms.graph import Graph
from ..data_loader import load_cities, load_graph
from ..errors import NotFoundError

PRESET_ORDER = [
    "p1-bauru-vizinhos",
    "p2-regiao-bauru",
    "p3-estado-sp",
    "p4-regioes-separadas",
    "p5-litoral-norte",
]


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    graph: Graph
    warnings: list[str]
    discarded: list[dict[str, str]]
    include_manual: bool

    def summary(self) -> dict[str, object]:
        components = self.graph.connected_components()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "n_nodes": self.graph.n_nodes,
            "n_edges": self.graph.n_edges,
            "n_components": len(components),
            "include_manual": self.include_manual,
        }


def _normalize_name(value: str) -> str:
    """Compara nomes ignorando acentos, maiúsculas, hífens e espaços extras."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(without_accents.casefold().replace("-", " ").split())


@lru_cache(maxsize=1)
def _city_ids_by_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for city in load_cities():
        key = _normalize_name(city.name)
        if key in mapping:
            raise RuntimeError(
                f"Nome de município ambíguo nos dados: {city.name!r}. "
                "Os presets precisam de nomes únicos em São Paulo."
            )
        mapping[key] = city.id
    return mapping


def _city_id(name: str) -> str:
    try:
        return _city_ids_by_name()[_normalize_name(name)]
    except KeyError as exc:
        raise RuntimeError(
            f"Município necessário para um preset não encontrado: {name!r}"
        ) from exc


def bfs_ball(graph: Graph, start: str, radius: int) -> set[str]:
    """Vértices a até ``radius`` saltos de ``start`` (vizinhança em hops)."""
    graph.get_node(start)
    visited = {start}
    frontier = {start}
    for _ in range(radius):
        next_frontier: set[str] = set()
        for node_id in frontier:
            next_frontier.update(graph.neighbors(node_id))
        next_frontier -= visited
        if not next_frontier:
            break
        visited |= next_frontier
        frontier = next_frontier
    return visited


def _preset_p1() -> Preset:
    full = load_graph(include_manual=True)
    centre = _city_id("Bauru")
    selected = bfs_ball(full, centre, radius=1)
    if not 8 <= len(selected) <= 15:
        raise RuntimeError(
            "O preset 'Bauru e vizinhos' saiu do intervalo esperado de 8 a 15 "
            f"vértices (obtido: {len(selected)}). Verifique os dados de divisa."
        )
    graph = full.induced_subgraph(selected)
    return Preset(
        id="p1-bauru-vizinhos",
        name="Bauru e vizinhos diretos",
        description=(
            "Bauru e todos os municípios que fazem divisa com ele. "
            "Grafo pequeno, com resultado verificável manualmente."
        ),
        graph=graph,
        warnings=list(graph.warnings),
        discarded=[],
        include_manual=True,
    )


def _preset_p2() -> Preset:
    full = load_graph(include_manual=True)
    centre = _city_id("Bauru")
    valid: list[tuple[int, set[str]]] = []
    for radius in range(1, 5):
        ball = bfs_ball(full, centre, radius=radius)
        if 60 <= len(ball) <= 150:
            valid.append((radius, ball))
    if not valid:
        raise RuntimeError(
            "Nenhum raio de 1 a 4 a partir de Bauru produziu um preset entre "
            "60 e 150 vértices. Verifique os dados."
        )
    radius, selected = max(valid, key=lambda item: item[0])
    graph = full.induced_subgraph(selected)
    return Preset(
        id="p2-regiao-bauru",
        name="Região de Bauru",
        description=(
            f"Municípios a até {radius} ligações de distância de Bauru. "
            "Grafo de tamanho médio, útil para comparar tempos e métricas."
        ),
        graph=graph,
        warnings=list(graph.warnings),
        discarded=[],
        include_manual=True,
    )


def _preset_p3() -> Preset:
    full = load_graph(include_manual=False)
    graph = full.largest_component()
    selected = set(graph.node_ids)
    discarded = [
        {
            "id": city.id,
            "name": city.name,
            "reason": "Fora do maior componente conexo: sem ligações por divisa.",
        }
        for city in sorted(full.nodes.values(), key=lambda item: item.id)
        if city.id not in selected
    ]
    warnings = list(graph.warnings)
    if discarded:
        names = ", ".join(item["name"] for item in discarded)
        warnings.append(
            f"Esta instância não inclui ligações manuais. {names} ficou isolada "
            "e foi descartada do maior componente conexo."
        )
    return Preset(
        id="p3-estado-sp",
        name="Estado de São Paulo (maior componente)",
        description=(
            "Todos os municípios paulistas ligados por divisa terrestre, "
            "mantendo apenas o maior componente conexo. É o caso grande do "
            "projeto: inviável de resolver manualmente."
        ),
        graph=graph,
        warnings=warnings,
        discarded=discarded,
        include_manual=False,
    )


def _preset_p4() -> Preset:
    full = load_graph(include_manual=True)
    bauru = bfs_ball(full, _city_id("Bauru"), radius=1)
    prudente = bfs_ball(full, _city_id("Presidente Prudente"), radius=1)
    graph = full.induced_subgraph(bauru | prudente)
    if len(graph.connected_components()) < 2:
        raise RuntimeError(
            "O preset de duas regiões separadas ficou conexo. Escolha outro par "
            "de cidades distantes."
        )
    return Preset(
        id="p4-regioes-separadas",
        name="Duas regiões separadas (floresta)",
        description=(
            "União de Bauru e vizinhos com Presidente Prudente e vizinhos. "
            "O grafo é desconexo: o sistema deve calcular uma floresta geradora "
            "mínima e avisar que não existe uma única árvore geradora."
        ),
        graph=graph,
        warnings=list(graph.warnings),
        discarded=[],
        include_manual=True,
    )


def _preset_p5() -> Preset:
    names = ["Ilhabela", "São Sebastião", "Bertioga", "Caraguatatuba"]
    selected = {_city_id(name) for name in names}
    full = load_graph(include_manual=True)
    graph = full.induced_subgraph(selected)
    manual_edges = [
        edge for edge in graph.edges if edge.attrs.get("source") == "manual"
    ]
    if not manual_edges:
        raise RuntimeError(
            "O preset do litoral norte deveria incluir a ligação manual "
            "Ilhabela–São Sebastião (balsa). Verifique data/manual/extras.csv."
        )
    return Preset(
        id="p5-litoral-norte",
        name="Litoral norte: Ilhabela com e sem balsa",
        description=(
            "Ilhabela, São Sebastião, Bertioga e Caraguatatuba. Inclui a ligação "
            "manual por balsa entre Ilhabela e São Sebastião; sem ela, Ilhabela "
            "ficaria isolada."
        ),
        graph=graph,
        warnings=list(graph.warnings),
        discarded=[],
        include_manual=True,
    )


def city_id_by_name(name: str) -> str:
    """Resolve o código IBGE pelo nome, ignorando acentos e hífens.

    Usado pelo benchmark e por qualquer serviço que receba um nome de cidade.
    """
    try:
        return _city_ids_by_name()[_normalize_name(name)]
    except KeyError as exc:
        raise NotFoundError(f"Município não encontrado pelo nome: {name!r}") from exc


@lru_cache(maxsize=1)
def get_presets() -> tuple[Preset, ...]:
    """Monta (uma única vez por processo) todas as instâncias prontas."""
    builders = {
        "p1-bauru-vizinhos": _preset_p1,
        "p2-regiao-bauru": _preset_p2,
        "p3-estado-sp": _preset_p3,
        "p4-regioes-separadas": _preset_p4,
        "p5-litoral-norte": _preset_p5,
    }
    return tuple(builders[preset_id]() for preset_id in PRESET_ORDER)


def get_preset(preset_id: str) -> Preset:
    """Busca um preset pelo id ou lança 404."""
    for preset in get_presets():
        if preset.id == preset_id:
            return preset
    raise NotFoundError(f"Instância pronta não encontrada: {preset_id}")
