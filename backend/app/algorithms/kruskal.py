"""Algoritmo de Kruskal para árvore geradora mínima.

Ideia: ordenar todas as arestas por peso e aceitar cada uma somente se ela
ligar dois componentes diferentes. O Union-Find faz essa verificação.

Complexidade: O(E log E) para ordenar + O(E α(V)) para o Union-Find.
Como E ≤ V², também se escreve O(E log V).
"""

from __future__ import annotations

import time
from typing import Any

from .graph import Edge, Graph, node_index
from .result import MSTResult
from .union_find import UnionFind


def _run_kruskal(
    graph: Graph, trace: bool
) -> tuple[MSTResult, list[dict[str, Any]] | None]:
    """Executa o núcleo do algoritmo, opcionalmente gravando o trace.

    As duas fases do algoritmo são cronometradas separadamente com
    ``time.perf_counter`` (PLAN §6.4): ``sort_time_ms`` cobre a ordenação das
    arestas e ``loop_time_ms`` cobre o laço principal. Na passada com trace os
    valores refletem a passada instrumentada, mas o chamador ``kruskal``
    substitui ``metrics`` pelos valores da passada limpa.
    """
    sort_start = time.perf_counter()
    # Ordena por (peso, índice menor, índice maior) — PLAN §6.2. O índice é o
    # do vértice na ordenação numérica/alfabética (BUG-002), não a string.
    index = node_index(graph.node_ids)
    order = sorted(
        graph.edges,
        key=lambda edge: (
            edge.weight,
            min(index[edge.u], index[edge.v]),
            max(index[edge.u], index[edge.v]),
        ),
    )
    sort_time_ms = (time.perf_counter() - sort_start) * 1000.0
    events: list[dict[str, Any]] | None = [] if trace else None
    if events is not None:
        # PLAN §6.5: evento `sorted` registra a ordenação das arestas por peso.
        events.append({"type": "sorted", "step": 0, "n_edges": len(order)})
    components = graph.connected_components()
    component_count = len(components)
    target_edges = graph.n_nodes - component_count

    union_find = UnionFind(graph.node_ids)
    accepted: list[Edge] = []
    total_cost = 0.0
    examined = 0
    rejected = 0

    loop_start = time.perf_counter()
    for edge in order:
        examined += 1
        root_u = union_find.find(edge.u)
        root_v = union_find.find(edge.v)
        same_component = root_u == root_v

        if events is not None:
            events.append(
                {
                    "type": "consider",
                    "step": examined,
                    "edge": edge.as_dict(),
                    "component_u_size": union_find.size[root_u],
                    "component_v_size": union_find.size[root_v],
                    "same_component": same_component,
                }
            )

        if same_component:
            # Os dois extremos já estão no mesmo componente: aceitar fecharia
            # um ciclo. Pela propriedade do ciclo, a aresta pode ser descartada.
            rejected += 1
            if events is not None:
                events.append(
                    {
                        "type": "reject",
                        "step": examined,
                        "edge": edge.as_dict(),
                        "reason": "mesmo componente (formaria ciclo)",
                    }
                )
            continue

        # Extremos em componentes diferentes: a aresta é segura (propriedade
        # do corte) e é aceita; os componentes são unidos.
        union_find.union(edge.u, edge.v)
        accepted.append(edge)
        total_cost += edge.weight
        if events is not None:
            events.append(
                {
                    "type": "accept",
                    "step": examined,
                    "edge": edge.as_dict(),
                    "total_cost_so_far": total_cost,
                    "accepted_count": len(accepted),
                }
            )

        # Em grafo conexo, paramos em n-1 arestas. Em grafo desconexo, em n-c.
        if len(accepted) == target_edges:
            if events is not None:
                # PLAN §6.5: evento `stop(motivo)` registra a parada em n - c.
                events.append(
                    {
                        "type": "stop",
                        "step": examined,
                        "reason": (
                            f"floresta completa: {len(accepted)} aresta(s) "
                            f"aceitas (n - c = {graph.n_nodes} - {component_count})"
                        ),
                        "accepted_count": len(accepted),
                    }
                )
            break

    loop_time_ms = (time.perf_counter() - loop_start) * 1000.0

    result = MSTResult(
        algorithm="kruskal",
        edges=accepted,
        total_cost=total_cost,
        n_components=component_count,
        components=components,
        is_forest=True,  # por construção, nunca há ciclo
        metrics={
            "time_ms": 0.0,
            "sort_time_ms": round(sort_time_ms, 3),
            "loop_time_ms": round(loop_time_ms, 3),
            "edges_examined": examined,
            "accepted": len(accepted),
            "rejected": rejected,
            "find_calls": union_find.find_calls,
            "union_calls": union_find.union_calls,
        },
        trace=events,
    )
    return result, events


def kruskal(graph: Graph, trace: bool = False) -> MSTResult:
    """Calcula a árvore (ou floresta) geradora mínima com Kruskal.

    Se ``trace=True``, uma passada com eventos é executada para a animação e
    uma passada limpa separada é usada para medir o tempo, como pede o plano.
    """
    if trace:
        traced_result, events = _run_kruskal(graph, trace=True)
        start = time.perf_counter()
        clean_result, _ = _run_kruskal(graph, trace=False)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        clean_result.metrics["time_ms"] = round(elapsed_ms, 3)
        traced_result.metrics = clean_result.metrics
        traced_result.trace = events
        return traced_result

    start = time.perf_counter()
    result, _ = _run_kruskal(graph, trace=False)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    result.metrics["time_ms"] = round(elapsed_ms, 3)
    result.trace = None
    return result
