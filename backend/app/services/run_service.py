"""Execução dos algoritmos e montagem da comparação Prim × Kruskal."""

from __future__ import annotations

from typing import Any, Literal

from ..algorithms.graph import Edge, Graph
from ..algorithms.kruskal import kruskal
from ..algorithms.prim import prim
from ..algorithms.result import MSTResult
from ..algorithms.verify import verify_forest
from ..errors import ValidationError
from .serialization import graph_stats

AlgorithmChoice = Literal["kruskal", "prim", "both"]


def _edge_pairs(edges: list[Edge]) -> set[tuple[str, str]]:
    return {edge.pair for edge in edges}


def compare_results(
    graph: Graph,
    kruskal_result: MSTResult | None,
    prim_result: MSTResult | None,
) -> dict[str, Any]:
    """Compara custo, arestas e empates dos dois algoritmos."""
    if kruskal_result is None or prim_result is None:
        return {
            "same_cost": None,
            "same_edges": None,
            "cost_difference": None,
            "has_weight_ties": None,
            "kruskal_only_edges": [],
            "prim_only_edges": [],
            "is_consistent": None,
            "message": "Execute os dois algoritmos para ver a comparação completa.",
        }

    cost_difference = abs(kruskal_result.total_cost - prim_result.total_cost)
    same_cost = cost_difference <= 1e-6
    kruskal_pairs = _edge_pairs(kruskal_result.edges)
    prim_pairs = _edge_pairs(prim_result.edges)
    same_edges = kruskal_pairs == prim_pairs

    weights = [edge.weight for edge in graph.edges]
    has_weight_ties = len(weights) != len(set(weights))

    kruskal_only = [
        edge.as_dict()
        for edge in kruskal_result.edges
        if edge.pair not in prim_pairs
    ]
    prim_only = [
        edge.as_dict()
        for edge in prim_result.edges
        if edge.pair not in kruskal_pairs
    ]

    if not same_cost:
        message = (
            "ERRO GRAVE: Prim e Kruskal produziram custos diferentes. "
            "Isso indica um problema na implementação, não uma diferença teórica."
        )
    elif same_edges:
        message = (
            "Mesmo custo total e mesmo conjunto de arestas. "
            "As duas abordagens chegaram à mesma árvore geradora mínima."
        )
    elif has_weight_ties:
        message = (
            "Mesmo custo total, mas conjuntos de arestas diferentes. "
            "Há pesos empatados no grafo, então podem existir várias MSTs de "
            "mesmo custo; a escolha entre elas depende do critério de desempate."
        )
    else:
        message = (
            "Mesmo custo total, mas conjuntos diferentes sem empates de peso. "
            "Com pesos distintos a MST é única; isso indica um problema na "
            "implementação."
        )

    return {
        "same_cost": same_cost,
        "same_edges": same_edges,
        "cost_difference": cost_difference,
        "has_weight_ties": has_weight_ties,
        "kruskal_only_edges": kruskal_only,
        "prim_only_edges": prim_only,
        "is_consistent": same_cost and (same_edges or has_weight_ties),
        "message": message,
    }


def run_algorithms(
    graph: Graph,
    algorithm: AlgorithmChoice = "both",
    start_vertex: str | None = None,
    trace: bool = False,
    verify: bool = True,
) -> dict[str, Any]:
    """Executa a escolha do usuário sobre um grafo já validado."""
    if algorithm not in ("kruskal", "prim", "both"):
        raise ValidationError("Algoritmo inválido. Use 'kruskal', 'prim' ou 'both'.")
    if start_vertex is not None and start_vertex not in graph.nodes:
        raise ValidationError(f"Vértice inicial inexistente no grafo: {start_vertex}")

    results: dict[str, MSTResult | None] = {"kruskal": None, "prim": None}
    if algorithm in ("kruskal", "both"):
        results["kruskal"] = kruskal(graph, trace=trace)
    if algorithm in ("prim", "both"):
        results["prim"] = prim(graph, start_vertex=start_vertex, trace=trace)

    verification: dict[str, Any] | None = None
    if verify:
        verification = {}
        for name, result in results.items():
            if result is not None:
                verification[name] = verify_forest(graph, result).as_dict()

    return {
        "kruskal": results["kruskal"].as_dict() if results["kruskal"] else None,
        "prim": results["prim"].as_dict() if results["prim"] else None,
        "comparison": compare_results(graph, results["kruskal"], results["prim"]),
        "verification": verification,
        "graph_stats": graph_stats(graph),
        "warnings": list(graph.warnings),
    }
