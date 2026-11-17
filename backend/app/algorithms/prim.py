"""Algoritmo de Prim para árvore geradora mínima.

Ideia: crescer uma única árvore a partir de um vértice inicial. A cada passo,
uma fila de prioridade (heap) fornece a aresta de menor peso que liga a árvore
a um vértice ainda fora dela.

Complexidade com heap binário: O(E log V). Em grafo desconexo, o algoritmo é
reiniciado em cada componente, produzindo uma floresta geradora mínima.
"""

from __future__ import annotations

import heapq
import time
from typing import Any

from .graph import Edge, Graph, GraphValidationError, node_index
from .result import MSTResult


def _run_prim(
    graph: Graph,
    start_vertex: str,
    trace: bool,
) -> tuple[MSTResult, list[dict[str, Any]] | None]:
    """Executa o núcleo do Prim, opcionalmente gravando o trace."""
    visited: set[str] = set()
    accepted: list[Edge] = []
    components: list[list[str]] = []
    total_cost = 0.0

    # Índice numérico/alfabético dos vértices (PLAN §6.1): desempata o heap.
    index = node_index(graph.node_ids)

    heap: list[tuple[float, int, int, str, str, Edge]] = []
    heap_pushes = 0
    heap_pops = 0
    stale_pops = 0
    key_updates = 0
    # Menor chave conhecida de cada vértice ainda fora da árvore (peso da
    # aresta mais leve que o liga a ela). Ausente = ∞ (vértice descoberto).
    best_key: dict[str, float] = {}
    events: list[dict[str, Any]] | None = [] if trace else None
    step = 0

    def push_frontier(vertex: str) -> None:
        """Insere na fronteira as arestas de ``vertex`` para fora da árvore."""
        nonlocal heap_pushes, key_updates
        pushed: list[dict[str, Any]] = []
        updates: list[dict[str, Any]] = []
        for edge in graph.adjacency[vertex]:
            neighbor = edge.v if edge.u == vertex else edge.u
            if neighbor in visited:
                continue
            heapq.heappush(
                heap,
                (
                    edge.weight,
                    min(index[edge.u], index[edge.v]),
                    max(index[edge.u], index[edge.v]),
                    vertex,
                    neighbor,
                    edge,
                ),
            )
            heap_pushes += 1
            pushed.append(
                {
                    "u": vertex,
                    "v": neighbor,
                    "weight": edge.weight,
                }
            )
            # PLAN §6.5: update_key(v, antiga, nova, pai) — a chave do vizinho
            # só é reduzida quando esta aresta é mais leve que a conhecida
            # (∞ na descoberta inicial). A entrada antiga permanece no heap e
            # é descartada depois como obsoleta (skip/skip_stale).
            previous_key = best_key.get(neighbor)
            if previous_key is None or edge.weight < previous_key:
                key_updates += 1
                best_key[neighbor] = edge.weight
                if events is not None:
                    updates.append(
                        {
                            "type": "update_key",
                            "step": step,
                            "vertex": neighbor,
                            "old_key": previous_key,  # None = ∞ (descoberta)
                            "new_key": edge.weight,
                            "parent": vertex,
                            "edge": edge.as_dict(),
                            "heap_size": len(heap),
                        }
                    )
        if events is not None:
            if pushed:
                events.append(
                    {
                        "type": "push",
                        "step": step,
                        "vertex": vertex,
                        "edges": pushed,
                        "heap_size": len(heap),
                    }
                )
            events.extend(updates)

    # O primeiro vértice é o escolhido pelo usuário; os demais componentes
    # começam no menor id ainda não visitado (ordem determinística).
    remaining = [vertex for vertex in graph.node_ids if vertex != start_vertex]
    roots = [start_vertex] + remaining
    component_index = 0

    for root in roots:
        if root in visited:
            continue
        component_index += 1
        component_nodes = [root]

        if events is not None:
            events.append(
                {
                    "type": "start" if component_index == 1 else "restart",
                    "step": step,
                    "vertex": root,
                    "component_index": component_index,
                }
            )

        visited.add(root)
        push_frontier(root)

        while heap:
            weight, _, _, source, target, edge = heapq.heappop(heap)
            heap_pops += 1
            step += 1
            tree_size = len(component_nodes)
            cut_size = graph.n_nodes - tree_size

            if events is not None:
                events.append(
                    {
                        "type": "pop",
                        "step": step,
                        "edge": edge.as_dict(),
                        "heap_size": len(heap),
                    }
                )
                # PLAN §6.5: extract(v, chave, pai, tamanho do corte). O vértice
                # ``target`` ainda está fora da árvore neste ponto.
                events.append(
                    {
                        "type": "extraction",
                        "step": step,
                        "vertex": target,
                        "key": weight,
                        "parent": source,
                        "tree_size": tree_size,
                        "cut_size": cut_size,
                        "edge": edge.as_dict(),
                        "heap_size": len(heap),
                        "component_index": component_index,
                    }
                )

            if target in visited:
                # Entrada obsoleta: o destino entrou na árvore por outra aresta
                # mais leve depois que esta foi inserida no heap.
                stale_pops += 1
                if events is not None:
                    events.append(
                        {
                            "type": "skip",
                            "step": step,
                            "edge": edge.as_dict(),
                            "reason": "obsoleta (destino já está na árvore)",
                        }
                    )
                    # PLAN §6.5: skip_stale(v).
                    events.append(
                        {
                            "type": "skip_stale",
                            "step": step,
                            "vertex": target,
                            "key": weight,
                            "parent": source,
                            "reason": "obsoleta (destino já está na árvore)",
                        }
                    )
                continue

            # A aresta é a mais leve que cruza o corte (árvore, restante).
            # Pela propriedade do corte, ela é segura para a MST.
            visited.add(target)
            component_nodes.append(target)
            accepted.append(edge)
            total_cost += weight

            if events is not None:
                events.append(
                    {
                        "type": "accept",
                        "step": step,
                        "edge": edge.as_dict(),
                        "from_vertex": source,
                        "new_vertex": target,
                        "tree_size": len(component_nodes),
                        "cut_size": graph.n_nodes - len(component_nodes),
                        "total_cost_so_far": total_cost,
                        "component_index": component_index,
                    }
                )

            push_frontier(target)

        components.append(sorted(component_nodes, key=lambda node_id: index[node_id]))

    result = MSTResult(
        algorithm="prim",
        edges=accepted,
        total_cost=total_cost,
        n_components=len(components),
        components=components,
        is_forest=True,
        metrics={
            "time_ms": 0.0,
            "edges_examined": heap_pops,
            "accepted": len(accepted),
            "heap_pushes": heap_pushes,
            "heap_pops": heap_pops,
            "stale_pops": stale_pops,
            "key_updates": key_updates,
        },
        trace=events,
    )
    return result, events


def prim(
    graph: Graph,
    start_vertex: str | None = None,
    trace: bool = False,
) -> MSTResult:
    """Calcula a árvore (ou floresta) geradora mínima com Prim.

    ``start_vertex`` é o vértice inicial; por padrão usa o menor id. Se o
    grafo for desconexo, o algoritmo reinicia em cada componente.
    """
    if start_vertex is None:
        start_vertex = graph.node_ids[0]
    if start_vertex not in graph.nodes:
        raise GraphValidationError(f"Vértice inicial inexistente: {start_vertex}")

    if trace:
        traced_result, events = _run_prim(graph, start_vertex, trace=True)
        start = time.perf_counter()
        clean_result, _ = _run_prim(graph, start_vertex, trace=False)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        clean_result.metrics["time_ms"] = round(elapsed_ms, 3)
        traced_result.metrics = clean_result.metrics
        traced_result.trace = events
        return traced_result

    start = time.perf_counter()
    result, _ = _run_prim(graph, start_vertex, trace=False)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    result.metrics["time_ms"] = round(elapsed_ms, 3)
    result.trace = None
    return result
