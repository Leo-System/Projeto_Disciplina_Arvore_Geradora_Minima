"""Catálogo de municípios e montagem do grafo por seleção do usuário."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from ..algorithms.graph import Graph
from ..data_loader import load_cities, load_graph
from ..errors import ValidationError


MAX_ADDED_CITIES_IN_WARNING = 20


@dataclass(frozen=True)
class BuiltGraph:
    graph: Graph
    warnings: list[str]
    discarded: list[dict[str, str]]


@lru_cache(maxsize=1)
def city_catalog() -> tuple[dict[str, object], ...]:
    """Lista de municípios com coordenadas e vizinhos (para o frontend)."""
    full = load_graph(include_manual=True)
    catalog: list[dict[str, object]] = []
    for city in sorted(load_cities(), key=lambda item: item.name.casefold()):
        catalog.append(
            {
                "id": city.id,
                "name": city.name,
                "lat": city.lat,
                "lon": city.lon,
                "neighbors": sorted(full.neighbors(city.id)),
            }
        )
    return tuple(catalog)


def _component_index(graph: Graph) -> dict[str, int]:
    """Mapeia cada vértice para o índice do seu componente conexo."""
    index: dict[str, int] = {}
    for component_index, component in enumerate(graph.connected_components()):
        for node_id in component:
            index[node_id] = component_index
    return index


def _spans_multiple_components(graph: Graph, node_ids: Iterable[str]) -> bool:
    """True se os vértices informados estão em mais de um componente do grafo."""
    component_of = _component_index(graph)
    return len({component_of[node_id] for node_id in node_ids}) > 1


def _expand_until_connected(graph: Graph, selected: set[str]) -> set[str]:
    """Adiciona vizinhos em rodadas até o subgrafo induzido ficar conexo."""
    current = set(selected)
    while True:
        induced = graph.induced_subgraph(current)
        if len(induced.connected_components()) <= 1:
            return current

        expanded = set(current)
        for node_id in current:
            expanded.update(graph.neighbors(node_id))

        if expanded == current:
            raise ValidationError(
                "Não foi possível conectar os municípios selecionados: "
                "não há caminho entre eles."
            )

        current = expanded


def build_from_city_ids(
    city_ids: Iterable[str],
    include_manual: bool = True,
    connect_components: bool = False,
) -> BuiltGraph:
    """Monta o subgrafo induzido pela seleção de municípios.

    O grafo é formado pelas arestas cujas **duas** pontas estão selecionadas.
    Avisos são gerados para seleção insuficiente, cidades isoladas e grafo
    desconexo (este último vem da própria construção do grafo).

    Quando ``connect_components`` é verdadeiro, a seleção é expandida em
    rodadas (adicionando vizinhos de todos os selecionados) até o subgrafo
    induzido ficar conexo. Se necessário, as ligações manuais são
    automaticamente incluídas para viabilizar a conexão.
    """
    selected: list[str] = []
    for raw_id in city_ids:
        city_id = str(raw_id).strip()
        if city_id and city_id not in selected:
            selected.append(city_id)

    if len(selected) < 2:
        raise ValidationError(
            "Selecione ao menos 2 municípios para montar o grafo."
        )

    known_ids = {city.id for city in load_cities()}
    unknown = [city_id for city_id in selected if city_id not in known_ids]
    if unknown:
        raise ValidationError(
            f"Código(s) IBGE inexistente(s) na seleção: {', '.join(unknown[:10])}."
        )

    full = load_graph(include_manual=include_manual)

    if not connect_components:
        graph = full.induced_subgraph(selected)
        expanded = set(selected)
        auto_manual = False
    else:
        auto_manual = False

        if not include_manual and _spans_multiple_components(full, selected):
            full = load_graph(include_manual=True)
            auto_manual = True

        if _spans_multiple_components(full, selected):
            raise ValidationError(
                "Não foi possível conectar os municípios selecionados: "
                "não há caminho entre eles nem com as ligações manuais."
            )

        expanded = _expand_until_connected(full, set(selected))
        graph = full.induced_subgraph(expanded)

    warnings = list(graph.warnings)

    if auto_manual:
        warnings.append(
            "Ligações manuais foram incluídas automaticamente porque eram "
            "necessárias para conectar os municípios selecionados."
        )

    added_ids = sorted(
        expanded - set(selected),
        key=lambda node_id: (
            (full.nodes[node_id].name or node_id).casefold(),
            node_id,
        ),
    )
    if added_ids:
        names = [
            full.nodes[node_id].name or node_id
            for node_id in added_ids[:MAX_ADDED_CITIES_IN_WARNING]
        ]
        remaining = len(added_ids) - len(names)
        suffix = f" e mais {remaining}" if remaining > 0 else ""
        if len(added_ids) == 1:
            message = (
                "Para conectar a seleção, 1 município foi adicionado: "
                f"{names[0]}."
            )
        else:
            message = (
                f"Para conectar a seleção, {len(added_ids)} municípios foram "
                f"adicionados: {', '.join(names)}{suffix}."
            )
        warnings.append(message)

    node_names = {node.id: node.name for node in graph.nodes.values()}
    isolated = [
        node_id for node_id in graph.node_ids if not graph.adjacency[node_id]
    ]
    for node_id in isolated:
        warnings.append(
            f"O município {node_names[node_id]} ({node_id}) ficou isolado na seleção: "
            "nenhuma das suas ligações tem as duas pontas selecionadas."
        )

    # Remove avisos repetidos mantendo a ordem de descoberta.
    deduplicated = list(dict.fromkeys(warnings))
    return BuiltGraph(graph=graph, warnings=deduplicated, discarded=[])
