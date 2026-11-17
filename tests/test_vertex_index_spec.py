"""Regressão do BUG-002 — índice numérico dos vértices (PLAN §6.1 e §6.2).

Com ids de tamanho variável (ex.: ``"2"`` e ``"10"``) todos os desempates devem
ser **numéricos**; havendo qualquer id não numérico, a ordenação volta a ser
alfabética. Cobre ``Graph.node_ids``, ``connected_components``, a ordenação do
Kruskal e o heap do Prim.
"""

from __future__ import annotations

from backend.app.algorithms.graph import node_index
from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.prim import prim

from conftest import aresta, construir_grafo, no


def par_numerico(edge):
    """Extremos da aresta em ordem numérica, com o peso (ids são numéricos)."""
    u, v = edge.u, edge.v
    if int(u) > int(v):
        u, v = v, u
    return (u, v, float(edge.weight))


class TestNodeIndex:
    """Índice do vértice: numérico quando todos os ids são números."""

    def test_indice_numerico_quando_todos_os_ids_sao_numericos(self):
        assert node_index(["10", "2", "1"]) == {"1": 0, "2": 1, "10": 2}

    def test_indice_alfabetico_quando_ha_id_nao_numerico(self):
        # "A" quebra a hipótese de ids numéricos → ordem lexicográfica antiga.
        assert node_index(["10", "2", "A"]) == {"10": 0, "2": 1, "A": 2}


class TestOrdemDosVertices:
    """Graph.node_ids e connected_components seguem o índice numérico."""

    def test_node_ids_ordena_numericamente_ids_de_tamanho_variavel(self):
        grafo = construir_grafo([no(v) for v in ["10", "2", "1"]], [])

        # Ordem lexicográfica daria ["1", "10", "2"].
        assert grafo.node_ids == ["1", "2", "10"]

    def test_node_ids_usa_ordem_alfabetica_quando_ids_nao_sao_numericos(self):
        grafo = construir_grafo([no(v) for v in ["10", "2", "A"]], [])

        assert grafo.node_ids == ["10", "2", "A"]

    def test_connected_components_ordena_componentes_e_ids_numericamente(self):
        grafo = construir_grafo(
            [no(v) for v in ["10", "2", "11"]],
            [aresta("10", "11", 1)],
        )

        # Componente {2} antes de {10, 11} (2 < 10) e "10" antes de "11".
        # Ordem lexicográfica daria [["10", "11"], ["2"]].
        assert grafo.connected_components() == [["2"], ["10", "11"]]


class TestKruskalDesempateNumerico:
    """PLAN §6.2: ordenar arestas por (peso, índice menor, índice maior)."""

    def test_exame_das_arestas_usa_indice_numerico(self):
        grafo = construir_grafo(
            [no(v) for v in ["1", "2", "10"]],
            [aresta("1", "10", 1), aresta("1", "2", 1)],
        )

        resultado = kruskal(grafo)

        # Índices: 1→0, 2→1, 10→2. Chaves: 1-2=(0,1) e 1-10=(0,2),
        # logo a aresta 1-2 é examinada (e aceita) antes de 1-10.
        # Na ordem lexicográfica seria o contrário: "10" < "2".
        assert [par_numerico(e) for e in resultado.edges] == [
            ("1", "2", 1.0),
            ("1", "10", 1.0),
        ]

    def test_ciclo_com_ids_variaveis_desempata_numericamente(self):
        # Ciclo 1-2-10-11 com todos os pesos iguais (mesmo caso de K-16).
        grafo = construir_grafo(
            [no(v) for v in ["1", "2", "10", "11"]],
            [
                aresta("1", "2", 1),
                aresta("2", "10", 1),
                aresta("10", "11", 1),
                aresta("11", "1", 1),
            ],
        )

        resultado = kruskal(grafo)

        # Chaves: 1-2=(0,1), 1-11=(0,3), 2-10=(1,2), 10-11=(2,3) → exame
        # 1-2, 1-11, 2-10, 10-11; as três primeiras são aceitas e o laço para.
        assert [par_numerico(e) for e in resultado.edges] == [
            ("1", "2", 1.0),
            ("1", "11", 1.0),
            ("2", "10", 1.0),
        ]
        assert resultado.total_cost == 3.0


class TestPrimHeapNumerico:
    """PLAN §6.3: entradas do heap desempatadas pelo índice do vértice."""

    def test_heap_desempata_por_indice_numerico(self):
        grafo = construir_grafo(
            [no(v) for v in ["1", "2", "10"]],
            [aresta("1", "10", 1), aresta("1", "2", 1)],
        )

        resultado = prim(grafo)  # início padrão: menor índice ("1")

        # Mesmo desempate do Kruskal: 1-2 antes de 1-10 (1→0, 2→1, 10→2);
        # na ordem lexicográfica o heap devolveria 1-10 primeiro.
        assert [par_numerico(e) for e in resultado.edges] == [
            ("1", "2", 1.0),
            ("1", "10", 1.0),
        ]

    def test_reinicio_por_componente_usa_indice_numerico(self):
        grafo = construir_grafo(
            [no(v) for v in ["2", "10", "11"]],
            [aresta("10", "11", 1)],
        )

        resultado = prim(grafo)

        # Reinício no menor índice ainda não visitado: {2} antes de {10, 11}.
        assert resultado.components == [["2"], ["10", "11"]]
        assert [par_numerico(e) for e in resultado.edges] == [("10", "11", 1.0)]
