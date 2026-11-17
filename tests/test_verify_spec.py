"""Testes de especificação da verificação de florestas/MST."""

from __future__ import annotations

import pytest

from backend.app.algorithms.graph import Graph
from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.prim import prim
from backend.app.algorithms.verify import verify_forest
from conftest import (
    achar_aresta,
    aresta,
    conjunto_de_arestas,
    construir_grafo,
    construir_grafo_desconexo,
    no,
    resultado_com_arestas,
)


def _resultado_para(grafo, algoritmo):
    if algoritmo == "kruskal":
        return kruskal(grafo)
    return prim(grafo)


@pytest.mark.parametrize("algoritmo", ["kruskal", "prim"])
def test_verificacao_aprova_mst_correta(grafo_classico, algoritmo):
    resultado = _resultado_para(grafo_classico, algoritmo)

    verificacao = verify_forest(grafo_classico, resultado)

    assert isinstance(verificacao.is_forest, bool)
    assert isinstance(verificacao.cycle_property, bool)
    assert isinstance(verificacao.is_valid, bool)
    assert isinstance(verificacao.performed, bool)
    assert isinstance(verificacao.message, str)

    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_verificacao_reprova_resultado_com_ciclo(grafo_classico):
    resultado = kruskal(grafo_classico)
    aresta_extra = achar_aresta(grafo_classico, "A", "B")

    # A aresta A-B não pertence à MST clássica; adicioná-la cria um ciclo.
    assert ("A", "B", 4.0) not in conjunto_de_arestas(resultado)

    resultado_invalido = resultado_com_arestas(
        resultado, list(resultado.edges) + [aresta_extra]
    )
    verificacao = verify_forest(grafo_classico, resultado_invalido)

    assert verificacao.performed is True
    assert verificacao.is_valid is False
    assert (
        verificacao.is_forest is False
        or verificacao.cycle_property is False
    )


def test_verificacao_reprova_resultado_sem_todas_as_arestas(grafo_classico):
    resultado = kruskal(grafo_classico)

    # Remove uma aresta da árvore, mas mantém a alegação de um único componente.
    resultado_incompleto = resultado_com_arestas(
        resultado, list(resultado.edges)[:-1]
    )
    resultado_incompleto.n_components = 1
    resultado_incompleto.components = [sorted(grafo_classico.node_ids)]

    verificacao = verify_forest(grafo_classico, resultado_incompleto)

    assert verificacao.performed is True
    assert verificacao.is_valid is False


def test_verificacao_aprova_floresta_desconexa(grafo_desconexo):
    resultado = kruskal(grafo_desconexo)

    verificacao = verify_forest(grafo_desconexo, resultado)

    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_verificacao_aprova_grafo_sem_arestas():
    grafo = construir_grafo([no(v) for v in "ABCD"], [])
    resultado = kruskal(grafo)

    verificacao = verify_forest(grafo, resultado)

    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_verificacao_aprova_grafo_com_um_unico_vertice():
    grafo = construir_grafo([no("A")], [])
    resultado = prim(grafo)

    verificacao = verify_forest(grafo, resultado)

    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


@pytest.mark.parametrize("algoritmo", ["kruskal", "prim"])
def test_verificacao_aprova_mst_toda_negativa(algoritmo):
    # Triângulo cuja MST usa as arestas -10 e -5; a aresta externa -2 é maior
    # que o maior peso do caminho (-5). Antes da correção de _max_on_path, o
    # máximo iniciava em 0.0 e a propriedade do ciclo era falsamente violada.
    grafo = construir_grafo(
        [no(v) for v in "ABC"],
        [
            aresta("A", "B", -10),
            aresta("B", "C", -5),
            aresta("A", "C", -2),
        ],
    )
    resultado = _resultado_para(grafo, algoritmo)

    verificacao = verify_forest(grafo, resultado)

    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True
    assert resultado.total_cost == pytest.approx(-15.0)


def test_verificacao_em_grafo_grande_nao_exige_detalhes_internos():
    # Grafo completo com 350 vértices (61.075 arestas), grande o bastante para
    # exercitar um eventual limite de verificação detalhada.
    n = 350
    ids = [f"N{i:03d}" for i in range(n)]
    nodes = [no(vertice) for vertice in ids]
    edges = [
        aresta(ids[i], ids[j], float(i * 1000 + j + 1))
        for i in range(n)
        for j in range(i + 1, n)
    ]
    grafo = Graph.from_records(nodes, edges)
    resultado = kruskal(grafo)

    verificacao = verify_forest(grafo, resultado)

    assert isinstance(verificacao.performed, bool)
    assert isinstance(verificacao.is_forest, bool)
    assert isinstance(verificacao.message, str)
    assert verificacao.is_forest is True

    # Acima do limite, a verificação detalhada pode não ser executada.
    # Quando for executada, a MST deve ser aprovada.
    if verificacao.performed:
        assert verificacao.is_valid is True
