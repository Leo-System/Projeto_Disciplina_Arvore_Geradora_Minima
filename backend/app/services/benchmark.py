"""Análise de tempo: mediana e dispersão de Prim e Kruskal por tamanho.

Para o grafo do usuário, os tamanhos vêm de subgrafos induzidos crescentes:
os vértices entram em ordem de busca em largura (BFS), de modo que cada prefixo
seja o mais conectado possível, até o grafo completo. Para o preset histórico
(sem grafo), os tamanhos continuam vindo de subgrafos por raio de vizinhança
(em hops) a partir de Bauru, mais o estado completo.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import deque
from typing import Any

from ..algorithms.graph import Edge, Graph, Node, node_index
from ..algorithms.kruskal import kruskal
from ..algorithms.prim import prim
from ..errors import NotFoundError
from .presets import bfs_ball, city_id_by_name, get_preset

# Quantidade aproximada de linhas devolvidas para o grafo do usuário. O passo
# em vértices é derivado desse alvo para que grafos grandes não gerem dezenas
# de medições (cada linha custa ``runs`` execuções de cada algoritmo).
_TARGET_ROWS = 12


def _percentile(sorted_values: list[float], quantile: float) -> float:
    """Percentil com interpolação linear (suficiente para poucas amostras)."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def _measure(graph: Graph, algorithm: str, runs: int) -> dict[str, float]:
    """Executa um algoritmo ``runs`` vezes (com aquecimento) e resume o tempo."""
    # Aquecimento: descartado para reduzir efeitos de cache/importação.
    if algorithm == "kruskal":
        kruskal(graph)
    else:
        prim(graph)

    samples: list[float] = []
    for _ in range(runs):
        result = kruskal(graph) if algorithm == "kruskal" else prim(graph)
        samples.append(float(result.metrics["time_ms"]))
    samples.sort()
    return {
        "median": round(statistics.median(samples), 3),
        "p25": round(_percentile(samples, 0.25), 3),
        "p75": round(_percentile(samples, 0.75), 3),
        "min": round(samples[0], 3),
        "max": round(samples[-1], 3),
    }


# Instância densa determinística para a comparação esparso × denso (PLAN §7.5 / P1).
# Semente fixa para que a instância seja reproduzível entre execuções.
_DENSO_SEED = 20260335
_DENSO_N_NODES = 60


def _gerar_grafo_denso(
    n_nodes: int = _DENSO_N_NODES, seed: int = _DENSO_SEED
) -> Graph:
    """Gera um grafo denso determinístico (semente fixa).

    Usa ``random.Random(seed)`` para que a instância seja reproduzível. Cada par
    de vértices tem cerca de 70% de chance de gerar uma aresta com peso aleatório,
    resultando em um grafo denso adequado à comparação esparso × denso prevista no
    PLAN §7.5.
    """
    rng = random.Random(seed)
    node_ids = [f"denso-{i:03d}" for i in range(n_nodes)]
    nodes = [Node(id=nid, name=f"Denso {i:03d}") for i, nid in enumerate(node_ids)]
    edges: list[Edge] = []
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if rng.random() < 0.70:
                weight = round(rng.uniform(1.0, 100.0), 3)
                edges.append(Edge(node_ids[i], node_ids[j], weight))
    return Graph(nodes, edges)


def _growth_order(graph: Graph) -> list[str]:
    """Ordem determinística para crescer o grafo vértice a vértice.

    A busca em largura (por componente, começando pelo menor índice) garante
    que cada prefixo seja conexo sempre que o grafo original permitir. Assim
    os subgrafos medidos são instâncias válidas e comparáveis entre si, em vez
    de recortes arbitrários de vértices isolados.
    """
    index = node_index(graph.nodes)
    seen: set[str] = set()
    order: list[str] = []
    for root in sorted(graph.nodes, key=lambda node_id: index[node_id]):
        if root in seen:
            continue
        seen.add(root)
        queue: deque[str] = deque([root])
        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in sorted(
                graph.neighbors(current), key=lambda node_id: index[node_id]
            ):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return order


def progressive_subgraphs(
    graph: Graph, target_rows: int = _TARGET_ROWS
) -> tuple[list[Graph], int]:
    """Subgrafos induzidos crescentes até o grafo completo.

    Devolve ``(subgrafos, passo)``. O passo é o número de vértices entre duas
    medições consecutivas e é calculado para produzir cerca de ``target_rows``
    linhas: ``max(1, ceil(n / target_rows))``. O grafo completo é sempre a
    última medição, mesmo quando ``n`` não é múltiplo do passo.
    """
    n_nodes = graph.n_nodes
    step = max(1, math.ceil(n_nodes / max(1, target_rows)))
    order = _growth_order(graph)

    sizes = list(range(step, n_nodes + 1, step))
    if not sizes or sizes[-1] != n_nodes:
        sizes.append(n_nodes)
    # Medir um único vértice não diz nada sobre os algoritmos; o grafo
    # completo continua garantido mesmo para instâncias minúsculas.
    sizes = [size for size in sizes if size >= 2] or [n_nodes]

    graphs = [graph.induced_subgraph(order[:size]) for size in sizes]
    return graphs, step


def run_benchmark(
    graph: Graph | None = None,
    preset_id: str = "p3-estado-sp",
    runs: int = 20,
    start_city_name: str = "Bauru",
) -> dict[str, Any]:
    """Monta a tabela de tempos para a interface e o gráfico.

    Quando ``graph`` é fornecido, mede Kruskal e Prim diretamente nesse grafo
    (sem subgrafos por BFS e sem instância densa), respeitando o mesmo padrão
    usado pelo endpoint ``/run`` para o grafo do usuário. Caso contrário,
    mantém o comportamento histórico baseado no preset ``p3-estado-sp`` com
    subgrafos gerados por BFS a partir de Bauru.
    """
    runs = max(1, min(int(runs), 100))

    if graph is not None:
        # Caminho do grafo do usuário: mede subgrafos induzidos crescentes até
        # o grafo completo, para mostrar como o tempo cresce com o tamanho.
        graphs, step = progressive_subgraphs(graph)
        meta_preset_id = "user-graph"
        meta_preset_name = "Grafo do usuário"
        meta_start_city = ""
        meta_start_city_name = ""
        meta_dense = None
        meta_note = (
            "Mediana de execuções limpas (sem trace), precedidas de uma "
            "execução de aquecimento descartada. Tempos em milissegundos. "
            "Medições em subgrafos induzidos crescentes do grafo informado, "
            f"em passos de {step} vértice(s), até o grafo completo "
            f"({graph.n_nodes} vértices, {graph.n_edges} arestas)."
        )
    else:
        # Caminho histórico: preset fixo com subgrafos por BFS a partir de Bauru.
        preset = get_preset(preset_id)
        base_graph = preset.graph
        start_city = city_id_by_name(start_city_name)
        if start_city not in base_graph.nodes:
            raise NotFoundError(
                f"A cidade inicial {start_city_name!r} não pertence à instância {preset_id}."
            )

        # Chaveado pelo conjunto de nós (e não pelo tamanho): dois subgrafos com a
        # mesma cardinalidade mas vértices diferentes não podem se sobrescrever.
        sizes: dict[frozenset[str], Graph] = {}
        for radius in range(1, 7):
            ball = bfs_ball(base_graph, start_city, radius)
            sizes.setdefault(frozenset(ball), base_graph.induced_subgraph(ball))
        sizes.setdefault(frozenset(base_graph.nodes), base_graph)
        # Instância densa determinística (PLAN §7.5 / P1) para comparação esparso × denso.
        grafo_denso = _gerar_grafo_denso()
        sizes.setdefault(frozenset(grafo_denso.node_ids), grafo_denso)

        graphs = sorted(sizes.values(), key=lambda g: (g.n_edges, g.n_nodes))
        meta_preset_id = preset.id
        meta_preset_name = preset.name
        meta_start_city = start_city
        meta_start_city_name = base_graph.nodes[start_city].name
        meta_dense = {
            "n_nodes": grafo_denso.n_nodes,
            "n_edges": grafo_denso.n_edges,
            "seed": _DENSO_SEED,
        }
        meta_note = (
            "Mediana de execuções limpas (sem trace), precedidas de uma "
            "execução de aquecimento descartada. Tempos em milissegundos. "
            "Inclui uma instância densa determinística (semente fixa) para "
            "comparação esparso × denso (PLAN §7.5 / P1)."
        )

    rows: list[dict[str, Any]] = []
    for g in graphs:
        kruskal_summary = _measure(g, "kruskal", runs)
        prim_summary = _measure(g, "prim", runs)
        rows.append(
            {
                "n_nodes": g.n_nodes,
                "n_edges": g.n_edges,
                "kruskal_ms": kruskal_summary["median"],
                "kruskal_p25_ms": kruskal_summary["p25"],
                "kruskal_p75_ms": kruskal_summary["p75"],
                "prim_ms": prim_summary["median"],
                "prim_p25_ms": prim_summary["p25"],
                "prim_p75_ms": prim_summary["p75"],
            }
        )

    meta: dict[str, Any] = {
        "preset_id": meta_preset_id,
        "preset_name": meta_preset_name,
        "start_city": meta_start_city,
        "start_city_name": meta_start_city_name,
        "runs": runs,
        "note": meta_note,
    }
    if meta_dense is not None:
        meta["dense_instance"] = meta_dense

    return {"rows": rows, "meta": meta}
