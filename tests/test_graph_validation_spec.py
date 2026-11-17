"""Testes de especificação da construção, validação e navegação de grafos."""

from __future__ import annotations

import pytest

from backend.app.algorithms.graph import Graph, GraphValidationError
from conftest import (
    aresta,
    construir_grafo,
    construir_grafo_classico,
    construir_grafo_desconexo,
    no,
    peso_da_aresta,
)


def test_construcao_basica_expoe_atributos_publicos():
    grafo = construir_grafo_classico()

    assert grafo.n_nodes == 6
    assert grafo.n_edges == 9
    assert set(grafo.node_ids) == set("ABCDEF")
    assert len(grafo.edges) == grafo.n_edges
    assert isinstance(grafo.warnings, list)
    assert all(isinstance(aviso, str) for aviso in grafo.warnings)

    # O atributo nodes deve ser mapeável por id.
    for vertice in "ABCDEF":
        assert vertice in grafo.nodes
        assert grafo.nodes[vertice] is not None

    assert sorted(peso_da_aresta(e) for e in grafo.edges) == [
        1.0,
        2.0,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        8.0,
        10.0,
    ]


def test_zero_vertices_gera_erro_de_validacao():
    with pytest.raises(GraphValidationError):
        Graph.from_records([], [])


@pytest.mark.parametrize(
    "aresta_invalida",
    [
        aresta("A", "Z", 1),
        aresta("Z", "B", 1),
    ],
    ids=["destino-inexistente", "origem-inexistente"],
)
def test_vertice_inexistente_em_aresta_gera_erro(aresta_invalida):
    nodes = [no("A"), no("B")]

    with pytest.raises(GraphValidationError):
        Graph.from_records(nodes, [aresta_invalida])


@pytest.mark.parametrize(
    "peso_invalido",
    ["abc", None, float("nan"), float("inf"), float("-inf")],
    ids=["texto", "none", "nan", "infinito", "infinito-negativo"],
)
def test_peso_invalido_gera_erro(peso_invalido):
    nodes = [no("A"), no("B")]

    with pytest.raises(GraphValidationError):
        Graph.from_records(nodes, [aresta("A", "B", peso_invalido)])


def test_laco_e_ignorado_e_registrado_como_aviso():
    grafo = construir_grafo(
        [no("A"), no("B")],
        [
            aresta("A", "A", 5),
            aresta("A", "B", 2),
        ],
    )

    assert grafo.n_nodes == 2
    assert grafo.n_edges == 1
    assert peso_da_aresta(grafo.edges[0]) == pytest.approx(2.0)
    assert grafo.warnings, "laço deve ser ignorado com aviso, não com erro"


def test_grafo_contendo_somente_um_laco_nao_tem_arestas():
    grafo = construir_grafo([no("A")], [aresta("A", "A", 1)])

    assert grafo.n_nodes == 1
    assert grafo.n_edges == 0
    assert grafo.warnings


@pytest.mark.parametrize(
    "pesos",
    [
        (5, 2),
        (2, 5),
    ],
    ids=["maior-primeiro", "menor-primeiro"],
)
def test_aresta_duplicada_mantem_a_de_menor_peso(pesos):
    grafo = construir_grafo(
        [no("A"), no("B")],
        [
            aresta("A", "B", pesos[0]),
            aresta("A", "B", pesos[1]),
        ],
    )

    assert grafo.n_edges == 1
    assert peso_da_aresta(grafo.edges[0]) == pytest.approx(2.0)
    assert isinstance(grafo.warnings, list)


def test_peso_negativo_e_aceito_sem_erro():
    grafo = construir_grafo([no("A"), no("B")], [aresta("A", "B", -7)])

    assert grafo.n_nodes == 2
    assert grafo.n_edges == 1
    assert peso_da_aresta(grafo.edges[0]) == pytest.approx(-7.0)
    assert isinstance(grafo.warnings, list)


def test_grafo_com_um_vertice_e_valido():
    grafo = construir_grafo([no("A")], [])

    assert grafo.n_nodes == 1
    assert grafo.n_edges == 0
    assert set(grafo.node_ids) == {"A"}
    assert [list(componente) for componente in grafo.connected_components()] == [
        ["A"]
    ]


def test_grafo_desconexo_e_valido_e_tem_warnings_como_lista():
    grafo = construir_grafo_desconexo()

    assert grafo.n_nodes == 5
    assert grafo.n_edges == 2
    assert isinstance(grafo.warnings, list)
    assert all(isinstance(aviso, str) for aviso in grafo.warnings)


def test_induced_subgraph_preserva_apenas_vertices_e_arestas_induzidas():
    grafo = construir_grafo_classico()

    subgrafo = grafo.induced_subgraph(["A", "B", "C"])

    assert subgrafo.n_nodes == 3
    assert subgrafo.n_edges == 3
    assert set(subgrafo.node_ids) == {"A", "B", "C"}
    assert sorted(peso_da_aresta(e) for e in subgrafo.edges) == [1.0, 2.0, 4.0]


def test_induced_subgraph_com_um_unico_vertice_nao_tem_arestas():
    grafo = construir_grafo_classico()

    subgrafo = grafo.induced_subgraph(["D"])

    assert subgrafo.n_nodes == 1
    assert subgrafo.n_edges == 0
    assert set(subgrafo.node_ids) == {"D"}


def test_connected_components_ordena_pelo_menor_id_e_e_deterministico():
    # A ordem de inserção das arestas é propositalmente diferente da ordem dos ids.
    grafo = construir_grafo(
        [no(v) for v in "ABCDE"],
        [
            aresta("D", "C", 2),
            aresta("B", "A", 1),
        ],
    )

    primeira_leitura = [list(c) for c in grafo.connected_components()]
    segunda_leitura = [list(c) for c in grafo.connected_components()]

    assert primeira_leitura == segunda_leitura
    assert [set(c) for c in primeira_leitura] == [
        {"A", "B"},
        {"C", "D"},
        {"E"},
    ]
    assert [min(c) for c in primeira_leitura] == ["A", "C", "E"]


def test_largest_component_devolve_o_subgrafo_da_maior_componente():
    grafo = construir_grafo(
        [no(v) for v in "ABCDE"],
        [
            aresta("A", "B", 1),
            aresta("B", "C", 2),
            aresta("D", "E", 3),
        ],
    )

    maior = grafo.largest_component()

    assert isinstance(maior, Graph)
    assert maior.n_nodes == 3
    assert maior.n_edges == 2
    assert set(maior.node_ids) == {"A", "B", "C"}
