"""Estruturas de grafo usadas pelos algoritmos de árvore geradora mínima.

Este módulo é puro: não conhece HTTP, arquivos ou banco de dados. Ele apenas
representa um grafo não direcionado, simples e ponderado, e oferece as
operações básicas usadas pelos algoritmos e pelos serviços.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


class GraphValidationError(ValueError):
    """Erro de entrada do grafo (violação das regras da seção 5.6)."""


@dataclass(frozen=True)
class Node:
    """Vértice do grafo.

    ``id`` é o identificador (para municípios, o código IBGE de 7 dígitos).
    ``name``, ``lat`` e ``lon`` são opcionais, pois grafos enviados pelo
    usuário podem não ter coordenadas.
    """

    id: str
    name: str | None = None
    lat: float | None = None
    lon: float | None = None


@dataclass(frozen=True)
class Edge:
    """Aresta não direcionada e ponderada.

    ``attrs`` guarda atributos extras (por exemplo, ``border_km`` e
    ``source``), que não participam do cálculo da MST.
    """

    u: str
    v: str
    weight: float
    attrs: Mapping[str, Any] = field(default_factory=dict)

    @property
    def pair(self) -> tuple[str, str]:
        """Par não ordenado de extremos, útil para deduplicação."""
        return (self.u, self.v) if self.u <= self.v else (self.v, self.u)

    def reversed(self) -> "Edge":
        """Mesma aresta com os extremos trocados."""
        return Edge(self.v, self.u, self.weight, self.attrs)

    def as_dict(self) -> dict[str, Any]:
        """Representação serializável (usada pela API)."""
        return {
            "u": self.u,
            "v": self.v,
            "weight": self.weight,
            "attrs": dict(self.attrs),
        }


def _is_number(value: Any) -> bool:
    """Aceita apenas números reais finitos (bool não é peso válido)."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_numeric_id(node_id: str) -> bool:
    """True se o id representa um inteiro (sinal opcional), ex.: ``"2"``, ``"10"``."""
    body = node_id[1:] if node_id.startswith("-") else node_id
    return body.isdecimal()


def node_index(node_ids: Iterable[str]) -> dict[str, int]:
    """Índice determinístico dos vértices (PLAN §6.1).

    O índice é a posição do id na lista ordenada e é a base de todos os
    desempates (ordem dos vértices, ordenação do Kruskal, heap do Prim).
    Quando **todos** os ids informados são numéricos a ordenação é numérica
    (``"2"`` antes de ``"10"``); havendo qualquer id não numérico, a ordenação
    é alfabética (lexicográfica por string).
    """
    ids = list(node_ids)
    if all(_is_numeric_id(node_id) for node_id in ids):
        ordered = sorted(ids, key=lambda node_id: (int(node_id), node_id))
    else:
        ordered = sorted(ids)
    return {node_id: position for position, node_id in enumerate(ordered)}


class Graph:
    """Grafo não direcionado, simples e ponderado.

    Regras de validação (seção 5.6 do plano):
    - vértice inexistente, peso inválido e grafo sem vértices são **erro**;
    - laço é ignorado com aviso;
    - aresta duplicada mantém a de menor peso, com aviso;
    - peso negativo é aceito com aviso;
    - grafo desconexo é permitido (os algoritmos produzem uma floresta).
    """

    def __init__(
        self,
        nodes: Iterable[Node],
        edges: Iterable[Edge],
        warnings: Iterable[str] | None = None,
    ) -> None:
        self._nodes: dict[str, Node] = {}
        for node in nodes:
            if not isinstance(node.id, str) or not node.id:
                raise GraphValidationError("Todo vértice precisa de um id não vazio.")
            if node.id in self._nodes:
                raise GraphValidationError(f"Vértice duplicado: {node.id}")
            self._nodes[node.id] = node

        if not self._nodes:
            raise GraphValidationError("O grafo precisa ter ao menos um vértice.")

        self._edges: list[Edge] = []
        seen_pairs: set[tuple[str, str]] = set()
        for edge in edges:
            if edge.u not in self._nodes or edge.v not in self._nodes:
                missing = [vertex for vertex in (edge.u, edge.v) if vertex not in self._nodes]
                raise GraphValidationError(
                    f"A aresta {edge.u}-{edge.v} referencia vértice inexistente: {missing}"
                )
            if edge.u == edge.v:
                # Laços nunca pertencem a uma árvore; são descartados com aviso.
                continue
            if not _is_number(edge.weight):
                raise GraphValidationError(
                    f"Peso inválido na aresta {edge.u}-{edge.v}: {edge.weight!r}"
                )
            pair = edge.pair
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if edge.u <= edge.v:
                self._edges.append(edge)
            else:
                self._edges.append(edge.reversed())

        self.warnings: list[str] = list(warnings or [])

        # Laços e duplicatas são detectados em from_records, que tem acesso aos
        # dados originais; aqui só registramos avisos de nível de grafo.
        self._build_adjacency()

        if self.n_nodes == 1:
            self.warnings.append(
                "Grafo com um único vértice: a árvore geradora é vazia e o custo é 0."
            )
        if self.n_nodes > 1 and self.n_edges == 0:
            self.warnings.append("Grafo sem arestas: todos os vértices estão isolados.")

        negative_edges = [edge for edge in self._edges if edge.weight < 0]
        if negative_edges:
            self.warnings.append(
                f"{len(negative_edges)} aresta(s) com peso negativo. Os algoritmos "
                "funcionam, mas no domínio de distâncias isso não faz sentido."
            )

        components = self.connected_components()
        if len(components) > 1:
            sizes = ", ".join(str(len(component)) for component in components[:5])
            suffix = "" if len(components) <= 5 else ", ..."
            self.warnings.append(
                f"Grafo desconexo: {len(components)} componentes "
                f"(tamanhos: {sizes}{suffix}). Será calculada uma floresta geradora mínima."
            )

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------

    @classmethod
    def from_records(
        cls,
        nodes: Iterable[Mapping[str, Any] | Node],
        edges: Iterable[Mapping[str, Any] | Edge],
    ) -> "Graph":
        """Valida e monta um grafo a partir de dicionários ou dataclasses.

        Esta é a porta de entrada usada pela API e pelos testes. Erros graves
        lançam :class:`GraphValidationError`; situações apenas suspeitas geram
        avisos em ``graph.warnings``.
        """
        normalized_nodes: list[Node] = []
        for raw_node in nodes:
            if isinstance(raw_node, Node):
                normalized_nodes.append(raw_node)
                continue
            node_id = raw_node.get("id")
            if not isinstance(node_id, str) or not node_id:
                raise GraphValidationError("Todo vértice precisa de um id não vazio.")
            lat = raw_node.get("lat")
            lon = raw_node.get("lon")
            for coordinate, label in ((lat, "latitude"), (lon, "longitude")):
                if coordinate is not None and not _is_number(coordinate):
                    raise GraphValidationError(
                        f"{label} inválida no vértice {node_id}: {coordinate!r}"
                    )
            normalized_nodes.append(
                Node(
                    id=node_id,
                    name=raw_node.get("name"),
                    lat=None if lat is None else float(lat),
                    lon=None if lon is None else float(lon),
                )
            )

        warnings: list[str] = []
        normalized_edges: list[Edge] = []
        best_by_pair: dict[tuple[str, str], tuple[float, int]] = {}
        edge_lookup: dict[tuple[str, str], Edge] = {}
        edge_order = 0

        for raw_edge in edges:
            if isinstance(raw_edge, Edge):
                u, v, weight, attrs = raw_edge.u, raw_edge.v, raw_edge.weight, raw_edge.attrs
            else:
                u = raw_edge.get("u")
                v = raw_edge.get("v")
                weight = raw_edge.get("weight")
                attrs = raw_edge.get("attrs") or {}
            if not isinstance(u, str) or not isinstance(v, str):
                raise GraphValidationError(
                    f"Extremos de aresta inválidos: {u!r}-{v!r}"
                )
            if u == v:
                warnings.append(f"Laço ignorado em {u}.")
                continue
            if not _is_number(weight):
                raise GraphValidationError(f"Peso inválido na aresta {u}-{v}: {weight!r}")
            pair = (u, v) if u <= v else (v, u)
            if pair in best_by_pair:
                previous_weight, _ = best_by_pair[pair]
                if float(weight) < previous_weight:
                    warnings.append(
                        f"Aresta duplicada {pair[0]}-{pair[1]}: mantida a de menor "
                        f"peso ({float(weight):.3f} em vez de {previous_weight:.3f})."
                    )
                    best_by_pair[pair] = (float(weight), edge_order)
                    edge_lookup[pair] = Edge(
                        pair[0], pair[1], float(weight), attrs or {}
                    )
                else:
                    warnings.append(
                        f"Aresta duplicada {pair[0]}-{pair[1]}: mantida a de menor "
                        f"peso ({previous_weight:.3f} em vez de {float(weight):.3f})."
                    )
                continue
            best_by_pair[pair] = (float(weight), edge_order)
            edge_lookup[pair] = Edge(pair[0], pair[1], float(weight), attrs or {})
            edge_order += 1

        normalized_edges.extend(edge_lookup.values())
        return cls(normalized_nodes, normalized_edges, warnings=warnings)

    def _build_adjacency(self) -> None:
        adjacency: dict[str, list[Edge]] = defaultdict(list)
        for node_id in self._nodes:
            adjacency[node_id]
        for edge in self._edges:
            adjacency[edge.u].append(edge)
            adjacency[edge.v].append(edge)
        for node_id, incident in adjacency.items():
            incident.sort(key=lambda item: (item.weight, item.pair))
            adjacency[node_id] = incident
        self._adjacency = dict(adjacency)

    # ------------------------------------------------------------------
    # Propriedades e consultas
    # ------------------------------------------------------------------

    @property
    def nodes(self) -> Mapping[str, Node]:
        """Mapeamento id -> vértice."""
        return self._nodes

    @property
    def edges(self) -> list[Edge]:
        """Lista de arestas (sem laços e sem duplicatas)."""
        return list(self._edges)

    @property
    def node_ids(self) -> list[str]:
        """Ids em ordem determinística (numérica se todos forem números)."""
        index = node_index(self._nodes)
        return sorted(self._nodes, key=lambda node_id: index[node_id])

    @property
    def n_nodes(self) -> int:
        return len(self._nodes)

    @property
    def n_edges(self) -> int:
        return len(self._edges)

    @property
    def adjacency(self) -> Mapping[str, list[Edge]]:
        """Lista de adjacência derivada das arestas."""
        return self._adjacency

    def get_node(self, node_id: str) -> Node:
        """Devolve o vértice ou lança erro se ele não existir."""
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise GraphValidationError(f"Vértice inexistente: {node_id}") from exc

    def neighbors(self, node_id: str) -> list[str]:
        """Ids dos vizinhos de um vértice, em ordem determinística."""
        self.get_node(node_id)
        return sorted(
            edge.v if edge.u == node_id else edge.u
            for edge in self._adjacency[node_id]
        )

    # ------------------------------------------------------------------
    # Operações estruturais
    # ------------------------------------------------------------------

    def connected_components(self) -> list[list[str]]:
        """Componentes conexos como listas de ids.

        A ordem é determinística pelo índice numérico dos vértices (PLAN §6.1):
        cada componente é ordenado internamente e a lista é ordenada pelo menor
        índice de cada componente.
        """
        index = node_index(self._nodes)
        remaining = set(self._nodes)
        components: list[list[str]] = []
        while remaining:
            start = min(remaining, key=lambda node_id: index[node_id])
            remaining.remove(start)
            queue: deque[str] = deque([start])
            component = [start]
            while queue:
                current = queue.popleft()
                for neighbor in self.neighbors(current):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        component.append(neighbor)
                        queue.append(neighbor)
            components.append(sorted(component, key=lambda node_id: index[node_id]))
        components.sort(key=lambda component: index[component[0]])
        return components

    def induced_subgraph(self, node_ids: Iterable[str]) -> "Graph":
        """Subgrafo induzido pelos vértices informados (seleção do usuário)."""
        selected = set(node_ids)
        unknown = sorted(selected - set(self._nodes))
        if unknown:
            raise GraphValidationError(f"Vértices inexistentes na seleção: {unknown}")
        if not selected:
            raise GraphValidationError("A seleção precisa ter ao menos um vértice.")

        selected_nodes = [self._nodes[node_id] for node_id in sorted(selected)]
        selected_edges = [
            edge for edge in self._edges if edge.u in selected and edge.v in selected
        ]
        return Graph(
            selected_nodes,
            selected_edges,
        )

    def largest_component(self) -> "Graph":
        """Subgrafo induzido pelo maior componente conexo.

        Em caso de empate, escolhe o primeiro componente na ordem por índice
        numérico (a mesma de :meth:`connected_components`), o que mantém o
        resultado determinístico.
        """
        components = self.connected_components()
        largest_size = max(len(component) for component in components)
        chosen = next(
            component for component in components if len(component) == largest_size
        )
        return self.induced_subgraph(chosen)
