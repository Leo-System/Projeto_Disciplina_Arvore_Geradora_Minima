"""Verificação independente de otimalidade da árvore geradora mínima.

A verificação não chama Kruskal nem Prim. Ela confere duas coisas:

1. **Estrutura**: o resultado tem ``n − c`` arestas, não forma ciclo e usa
   apenas arestas do grafo original.
2. **Propriedade do ciclo**: para toda aresta fora da árvore, seu peso é maior
   ou igual ao maior peso no caminho entre seus extremos dentro da árvore.
   Se isso vale, nenhuma aresta externa pode substituir uma aresta da árvore
   para produzir uma solução mais barata — é uma prova de otimalidade.

Para consultar o maior peso no caminho de forma eficiente, o verificador
pré-processa ancestrais com uma tabela binária (``up``) e o maior peso até
cada ancestral (``max_weight``). Cada consulta custa O(log V).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from .graph import Graph
from .result import MSTResult
from .union_find import UnionFind

DEFAULT_MAX_EDGES = 20_000
TOLERANCE = 1e-9


@dataclass
class VerificationResult:
    """Resultado da verificação exibido na interface."""

    performed: bool
    is_forest: bool
    cycle_property: bool
    is_valid: bool
    message: str
    cost_consistent: bool = True
    details: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "performed": self.performed,
            "is_forest": self.is_forest,
            "cycle_property": self.cycle_property,
            "is_valid": self.is_valid,
            "cost_consistent": self.cost_consistent,
            "message": self.message,
            "details": self.details,
        }


def _check_structure(graph: Graph, result: MSTResult) -> tuple[bool, bool, list[str]]:
    """Confere quantidade de arestas, ciclos e pertinência ao grafo original."""
    details: list[str] = []
    component_count = len(graph.connected_components())
    expected_edges = graph.n_nodes - component_count

    if len(result.edges) != expected_edges:
        details.append(
            f"Quantidade de arestas incorreta: esperadas {expected_edges} "
            f"(n − c), encontradas {len(result.edges)}."
        )

    graph_pairs = {edge.pair: edge for edge in graph.edges}
    union_find = UnionFind(graph.node_ids)
    for edge in result.edges:
        original = graph_pairs.get(edge.pair)
        if original is None:
            details.append(f"A aresta {edge.u}-{edge.v} não pertence ao grafo.")
            continue
        if abs(original.weight - edge.weight) > TOLERANCE:
            details.append(
                f"Peso divergente para a aresta {edge.u}-{edge.v}: "
                f"{edge.weight} x {original.weight}."
            )
        if not union_find.union(edge.u, edge.v):
            details.append(
                f"A aresta {edge.u}-{edge.v} fecha um ciclo na solução."
            )

    cost_sum = sum(edge.weight for edge in result.edges)
    cost_consistent = abs(cost_sum - result.total_cost) <= TOLERANCE
    if not cost_consistent:
        details.append(
            f"Custo total inconsistente: informado {result.total_cost}, "
            f"soma das arestas {cost_sum}."
        )

    is_forest = not details
    return is_forest, cost_consistent, details


def _build_lifting_tables(
    graph: Graph, result: MSTResult
) -> tuple[dict[str, int], list[dict[str, str]], list[dict[str, float]]]:
    """Pré-processa profundidade, ancestrais e maior peso no caminho."""
    node_ids = graph.node_ids
    tree_adjacency: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for edge in result.edges:
        tree_adjacency[edge.u].append((edge.v, edge.weight))
        tree_adjacency[edge.v].append((edge.u, edge.weight))

    depth: dict[str, int] = {}
    parent: dict[str, str] = {node_id: node_id for node_id in node_ids}
    parent_weight: dict[str, float] = {node_id: 0.0 for node_id in node_ids}

    for root in node_ids:
        if root in depth:
            continue
        depth[root] = 0
        stack = [root]
        while stack:
            current = stack.pop()
            for neighbor, weight in tree_adjacency[current]:
                if neighbor in depth:
                    continue
                depth[neighbor] = depth[current] + 1
                parent[neighbor] = current
                parent_weight[neighbor] = weight
                stack.append(neighbor)

    levels = max(1, len(node_ids).bit_length())
    up: list[dict[str, str]] = [parent]
    max_weight: list[dict[str, float]] = [parent_weight]
    for _ in range(1, levels):
        previous_up = up[-1]
        previous_max = max_weight[-1]
        current_up: dict[str, str] = {}
        current_max: dict[str, float] = {}
        for node_id in node_ids:
            middle = previous_up[node_id]
            current_up[node_id] = previous_up[middle]
            current_max[node_id] = max(previous_max[node_id], previous_max[middle])
        up.append(current_up)
        max_weight.append(current_max)

    return depth, up, max_weight


def _max_on_path(
    first: str,
    second: str,
    depth: dict[str, int],
    up: list[dict[str, str]],
    max_weight: list[dict[str, float]],
) -> float:
    """Maior peso de aresta no caminho entre dois vértices da árvore."""
    maximum = -math.inf

    if depth[first] < depth[second]:
        first, second = second, first

    difference = depth[first] - depth[second]
    level = 0
    while difference:
        if difference & 1:
            maximum = max(maximum, max_weight[level][first])
            first = up[level][first]
        difference >>= 1
        level += 1

    if first == second:
        return maximum

    for level in range(len(up) - 1, -1, -1):
        if up[level][first] != up[level][second]:
            maximum = max(maximum, max_weight[level][first], max_weight[level][second])
            first = up[level][first]
            second = up[level][second]

    maximum = max(maximum, max_weight[0][first], max_weight[0][second])
    return maximum


def verify_forest(
    graph: Graph,
    result: MSTResult,
    max_edges: int = DEFAULT_MAX_EDGES,
) -> VerificationResult:
    """Verifica estrutura e propriedade do ciclo de uma solução.

    Em grafos com mais de ``max_edges`` arestas, a propriedade do ciclo é
    pulada com aviso explícito; a estrutura continua sendo verificada.
    """
    is_forest, cost_consistent, details = _check_structure(graph, result)
    if not is_forest:
        return VerificationResult(
            performed=True,
            is_forest=False,
            cycle_property=False,
            is_valid=False,
            cost_consistent=cost_consistent,
            message="Solução inválida: " + " ".join(details),
            details=details,
        )

    if graph.n_edges > max_edges:
        message = (
            "Estrutura válida (floresta com n − c arestas e sem ciclos). "
            f"Propriedade do ciclo não verificada: o grafo tem {graph.n_edges} "
            f"arestas, acima do limite de {max_edges}."
        )
        return VerificationResult(
            performed=False,
            is_forest=True,
            cycle_property=False,
            is_valid=cost_consistent,
            cost_consistent=cost_consistent,
            message=message,
            details=[],
        )

    depth, up, max_weight = _build_lifting_tables(graph, result)
    tree_pairs = {edge.pair for edge in result.edges}
    violations: list[str] = []

    for edge in graph.edges:
        if edge.pair in tree_pairs:
            continue
        path_maximum = _max_on_path(edge.u, edge.v, depth, up, max_weight)
        if edge.weight < path_maximum - TOLERANCE:
            violations.append(
                f"A aresta {edge.u}-{edge.v} (peso {edge.weight:.3f}) é mais leve "
                f"que {path_maximum:.3f}, o maior peso no caminho da árvore."
            )

    if violations:
        return VerificationResult(
            performed=True,
            is_forest=True,
            cycle_property=False,
            is_valid=False,
            cost_consistent=cost_consistent,
            message="Propriedade do ciclo violada: " + " ".join(violations[:5]),
            details=violations,
        )

    outside_edges = graph.n_edges - len(result.edges)
    return VerificationResult(
        performed=True,
        is_forest=True,
        cycle_property=True,
        is_valid=cost_consistent,
        cost_consistent=cost_consistent,
        message=(
            "Floresta válida (n − c arestas, sem ciclos). Propriedade do ciclo "
            f"verificada em {outside_edges} aresta(s) fora da árvore."
        ),
        details=[],
    )
