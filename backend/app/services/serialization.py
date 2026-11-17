"""Serialização de grafos para a API.

Mantém um único formato de resposta para presets, seleção e uploads, de modo
que o frontend tenha um só caminho de código para desenhar o grafo.
"""

from __future__ import annotations

from typing import Any

from ..algorithms.graph import Graph


def graph_stats(graph: Graph) -> dict[str, Any]:
    """Resumo quantitativo usado pela interface."""
    components = graph.connected_components()
    divisa_edges = sum(
        1 for edge in graph.edges if edge.attrs.get("source") == "divisa"
    )
    manual_edges = sum(
        1 for edge in graph.edges if edge.attrs.get("source") == "manual"
    )
    return {
        "n_nodes": graph.n_nodes,
        "n_edges": graph.n_edges,
        "n_components": len(components),
        "is_connected": len(components) == 1,
        "n_divisa_edges": divisa_edges,
        "n_manual_edges": manual_edges,
        "component_sizes": sorted(
            (len(component) for component in components), reverse=True
        ),
    }


def graph_to_dict(
    graph: Graph,
    *,
    warnings: list[str] | None = None,
    discarded: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Formato JSON comum de um grafo."""
    return {
        "nodes": [
            {
                "id": node.id,
                "name": node.name,
                "lat": node.lat,
                "lon": node.lon,
            }
            for node in sorted(graph.nodes.values(), key=lambda item: item.id)
        ],
        "edges": [
            edge.as_dict()
            for edge in sorted(graph.edges, key=lambda item: item.pair)
        ],
        "warnings": list(warnings if warnings is not None else graph.warnings),
        "discarded": discarded or [],
        "stats": graph_stats(graph),
    }
