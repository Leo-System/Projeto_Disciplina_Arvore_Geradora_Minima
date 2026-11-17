"""Union-Find (conjuntos disjuntos) com compressão de caminho e união por tamanho.

É a estrutura que permite ao Kruskal detectar ciclos em tempo quase constante:
dois vértices estão no mesmo componente se, e somente se, têm a mesma raiz.
"""

from __future__ import annotations

from typing import Iterable


class UnionFind:
    """Conjuntos disjuntos com as duas otimizações clássicas.

    - **Compressão de caminho**: durante ``find``, cada nó visitado passa a
      apontar diretamente para a raiz.
    - **União por tamanho**: a árvore menor é pendurada sob a raiz da maior.

    Os contadores ``find_calls`` e ``union_calls`` são usados nas métricas da
    execução exibidas na interface.
    """

    def __init__(self, nodes: Iterable[str]) -> None:
        self.parent: dict[str, str] = {}
        self.size: dict[str, int] = {}
        for node in nodes:
            self.parent[node] = node
            self.size[node] = 1
        self.find_calls = 0
        self.union_calls = 0

    def find(self, node: str) -> str:
        """Devolve a raiz do conjunto que contém ``node`` (iterativo)."""
        self.find_calls += 1
        root = node
        while self.parent[root] != root:
            root = self.parent[root]

        # Segunda passada: comprime o caminho até a raiz.
        current = node
        while self.parent[current] != current:
            next_node = self.parent[current]
            self.parent[current] = root
            current = next_node
        return root

    def union(self, first: str, second: str) -> bool:
        """Une os conjuntos de ``first`` e ``second``.

        Devolve ``True`` se houve união e ``False`` se eles já eram o mesmo
        conjunto (o que indica que a aresta formaria um ciclo).
        """
        self.union_calls += 1
        root_first = self.find(first)
        root_second = self.find(second)
        if root_first == root_second:
            return False

        if self.size[root_first] < self.size[root_second]:
            root_first, root_second = root_second, root_first
        self.parent[root_second] = root_first
        self.size[root_first] += self.size[root_second]
        return True

    def connected(self, first: str, second: str) -> bool:
        """Indica se dois vértices já estão no mesmo componente."""
        return self.find(first) == self.find(second)

    def component_size(self, node: str) -> int:
        """Tamanho do componente que contém ``node``."""
        return self.size[self.find(node)]
