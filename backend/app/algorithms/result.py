"""Resultado padronizado dos algoritmos de árvore geradora mínima."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph import Edge


@dataclass
class MSTResult:
    """Saída comum de Kruskal e Prim.

    ``edges`` está na ordem em que as arestas foram aceitas, que é justamente
    a informação usada pela animação passo a passo.
    """

    algorithm: str
    edges: list[Edge]
    total_cost: float
    n_components: int
    components: list[list[str]]
    is_forest: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Formato enviado pela API (JSON)."""
        return {
            "algorithm": self.algorithm,
            "edges": [edge.as_dict() for edge in self.edges],
            "total_cost": self.total_cost,
            "n_components": self.n_components,
            "components": [
                {"size": len(component), "node_ids": component}
                for component in self.components
            ],
            "is_forest": self.is_forest,
            "metrics": self.metrics,
            "trace": self.trace,
        }
