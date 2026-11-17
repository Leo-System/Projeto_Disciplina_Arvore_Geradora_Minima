"""Testes de especificação dos algoritmos de Prim e Kruskal."""

from __future__ import annotations

import pytest

from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.prim import prim
from backend.app.algorithms.verify import verify_forest
from conftest import (
    aresta,
    campo_evento,
    conjunto_de_arestas,
    construir_grafo,
    custo_mst_networkx,
    gerar_grafo_conexo,
    no,
    tipo_evento,
)

MST_CLASSICA = sorted(
    [
        ("A", "C", 2.0),
        ("B", "C", 1.0),
        ("B", "D", 5.0),
        ("D", "E", 2.0),
        ("E", "F", 3.0),
    ]
)

MST_PESOS_NEGATIVOS = sorted(
    [
        ("A", "B", -5.0),
        ("B", "C", -2.0),
        ("C", "D", -1.0),
    ]
)

TIPOS_KRUSKAL = {"consider", "accept", "reject", "sorted", "stop"}
TIPOS_PRIM = {"start", "push", "pop", "accept", "skip", "restart", "extraction", "update_key", "skip_stale"}


def test_kruskal_calcula_mst_do_grafo_classico(grafo_classico):
    resultado = kruskal(grafo_classico)

    assert resultado.algorithm == "kruskal"
    assert resultado.total_cost == pytest.approx(13.0)
    assert len(resultado.edges) == 5
    assert resultado.n_components == 1
    assert resultado.is_forest is True
    assert resultado.trace is None
    assert conjunto_de_arestas(resultado) == MST_CLASSICA
    assert len(resultado.components) == 1
    assert set(resultado.components[0]) == set("ABCDEF")


def test_prim_calcula_mst_do_grafo_classico(grafo_classico):
    resultado = prim(grafo_classico)

    assert resultado.algorithm == "prim"
    assert resultado.total_cost == pytest.approx(13.0)
    assert len(resultado.edges) == 5
    assert resultado.n_components == 1
    assert resultado.is_forest is True
    assert resultado.trace is None
    assert conjunto_de_arestas(resultado) == MST_CLASSICA
    assert len(resultado.components) == 1
    assert set(resultado.components[0]) == set("ABCDEF")


def test_empates_de_peso_podem_gerar_msts_diferentes_mas_com_mesmo_custo(
    grafo_com_empates,
):
    resultado_kruskal = kruskal(grafo_com_empates)
    resultado_prim = prim(grafo_com_empates)

    for resultado in (resultado_kruskal, resultado_prim):
        assert resultado.total_cost == pytest.approx(3.0)
        assert len(resultado.edges) == 3
        assert resultado.n_components == 1
        assert resultado.is_forest is True
        assert verify_forest(grafo_com_empates, resultado).is_valid is True

    # Com empates, os conjuntos de arestas podem diferir; o custo não.
    assert resultado_kruskal.total_cost == pytest.approx(resultado_prim.total_cost)


def test_kruskal_usa_desempate_deterministico_em_caso_de_empate(
    grafo_com_empates,
):
    resultado = kruskal(grafo_com_empates)

    # Ordem determinística: (peso, menor id, maior id).
    # Aceita A-B, A-D e B-C; C-D seria rejeitada por formar ciclo.
    assert conjunto_de_arestas(resultado) == sorted(
        [
            ("A", "B", 1.0),
            ("A", "D", 1.0),
            ("B", "C", 1.0),
        ]
    )


def test_pesos_negativos_sao_suportados(grafo_com_pesos_negativos):
    resultado_kruskal = kruskal(grafo_com_pesos_negativos)
    resultado_prim = prim(grafo_com_pesos_negativos)

    for resultado in (resultado_kruskal, resultado_prim):
        assert resultado.total_cost == pytest.approx(-8.0)
        assert len(resultado.edges) == 3
        assert resultado.n_components == 1
        assert conjunto_de_arestas(resultado) == MST_PESOS_NEGATIVOS
        assert verify_forest(grafo_com_pesos_negativos, resultado).is_valid is True


def test_grafo_desconexo_gera_floresta_com_n_menos_c_arestas(grafo_desconexo):
    n = grafo_desconexo.n_nodes
    c = 3

    for resultado in (kruskal(grafo_desconexo), prim(grafo_desconexo)):
        assert resultado.n_components == c
        assert len(resultado.edges) == n - c
        assert resultado.total_cost == pytest.approx(3.0)
        assert resultado.is_forest is True
        assert conjunto_de_arestas(resultado) == sorted(
            [("A", "B", 1.0), ("C", "D", 2.0)]
        )
        assert sorted(min(componente) for componente in resultado.components) == [
            "A",
            "C",
            "E",
        ]
        assert verify_forest(grafo_desconexo, resultado).is_valid is True


def test_grafo_sem_arestas_tem_custo_zero_e_todos_os_vertices_isolados():
    grafo = construir_grafo([no(v) for v in "ABCD"], [])

    for resultado in (kruskal(grafo), prim(grafo)):
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 4
        assert len(resultado.components) == 4
        assert sorted(min(componente) for componente in resultado.components) == [
            "A",
            "B",
            "C",
            "D",
        ]
        assert resultado.is_forest is True
        assert verify_forest(grafo, resultado).is_valid is True


def test_grafo_com_um_vertice_retorna_resultado_vazio():
    grafo = construir_grafo([no("A")], [])

    for resultado in (kruskal(grafo), prim(grafo)):
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 1
        assert [list(componente) for componente in resultado.components] == [["A"]]
        assert resultado.is_forest is True
        assert verify_forest(grafo, resultado).is_valid is True


def test_dois_vertices_vizinhos_formam_uma_unica_aresta():
    grafo = construir_grafo([no("A"), no("B")], [aresta("A", "B", 7)])

    for resultado in (kruskal(grafo), prim(grafo)):
        assert len(resultado.edges) == 1
        assert resultado.total_cost == pytest.approx(7.0)
        assert resultado.n_components == 1
        assert conjunto_de_arestas(resultado) == [("A", "B", 7.0)]
        assert verify_forest(grafo, resultado).is_valid is True


def test_dois_vertices_nao_vizinhos_formam_dois_componentes():
    grafo = construir_grafo([no("A"), no("B")], [])

    for resultado in (kruskal(grafo), prim(grafo)):
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 2
        assert [min(componente) for componente in resultado.components] == ["A", "B"]
        assert resultado.is_forest is True
        assert verify_forest(grafo, resultado).is_valid is True


@pytest.mark.parametrize("inicio", list("ABCDEF"))
def test_prim_com_inicio_alternativo_continua_otimo(grafo_classico, inicio):
    resultado = prim(grafo_classico, start_vertex=inicio)

    assert resultado.total_cost == pytest.approx(13.0)
    assert len(resultado.edges) == 5
    assert resultado.n_components == 1
    # Neste grafo a MST é única, então o conjunto de arestas deve ser o mesmo.
    assert conjunto_de_arestas(resultado) == MST_CLASSICA
    assert verify_forest(grafo_classico, resultado).is_valid is True


def test_metricas_publicas_do_kruskal_estao_presentes(grafo_classico):
    resultado = kruskal(grafo_classico)

    for chave in (
        "time_ms",
        "edges_examined",
        "accepted",
        "rejected",
        "find_calls",
        "union_calls",
    ):
        assert chave in resultado.metrics
        assert isinstance(resultado.metrics[chave], (int, float))

    assert resultado.metrics["time_ms"] >= 0
    assert resultado.metrics["edges_examined"] >= len(resultado.edges)
    assert resultado.metrics["accepted"] == len(resultado.edges)
    assert resultado.metrics["rejected"] >= 0
    assert resultado.metrics["find_calls"] >= 0
    assert resultado.metrics["union_calls"] >= 0


def test_metricas_publicas_do_prim_estao_presentes(grafo_classico):
    resultado = prim(grafo_classico)

    for chave in (
        "time_ms",
        "edges_examined",
        "accepted",
        "heap_pushes",
        "heap_pops",
        "stale_pops",
    ):
        assert chave in resultado.metrics
        assert isinstance(resultado.metrics[chave], (int, float))

    assert resultado.metrics["time_ms"] >= 0
    assert resultado.metrics["accepted"] == len(resultado.edges)
    assert resultado.metrics["heap_pushes"] >= 0
    assert resultado.metrics["heap_pops"] >= resultado.metrics["stale_pops"] >= 0


def test_trace_do_kruskal_nao_altera_arestas_nem_custo(grafo_classico):
    sem_trace = kruskal(grafo_classico, trace=False)
    com_trace = kruskal(grafo_classico, trace=True)

    assert sem_trace.trace is None
    assert com_trace.trace is not None
    assert com_trace.total_cost == pytest.approx(sem_trace.total_cost)
    assert conjunto_de_arestas(com_trace) == conjunto_de_arestas(sem_trace)
    assert com_trace.n_components == sem_trace.n_components


def test_trace_do_kruskal_emite_eventos_essenciais(grafo_classico):
    resultado = kruskal(grafo_classico, trace=True)
    eventos = list(resultado.trace)

    assert eventos
    tipos = [tipo_evento(evento) for evento in eventos]
    assert set(tipos) <= TIPOS_KRUSKAL
    assert tipos[0] == "sorted"
    assert tipos[-1] == "stop"

    consideracoes = [
        evento for evento in eventos if tipo_evento(evento) == "consider"
    ]
    aceitacoes = [evento for evento in eventos if tipo_evento(evento) == "accept"]
    rejeicoes = [evento for evento in eventos if tipo_evento(evento) == "reject"]

    assert consideracoes
    assert aceitacoes
    assert rejeicoes

    for evento in consideracoes:
        assert isinstance(campo_evento(evento, "step"), int)
        assert campo_evento(evento, "edge") is not None
        assert isinstance(campo_evento(evento, "component_u_size"), int)
        assert isinstance(campo_evento(evento, "component_v_size"), int)
        assert isinstance(campo_evento(evento, "same_component"), bool)

    for evento in aceitacoes:
        assert isinstance(
            campo_evento(evento, "total_cost_so_far"), (int, float)
        )
        assert isinstance(campo_evento(evento, "accepted_count"), int)

    for evento in rejeicoes:
        motivo = campo_evento(evento, "reason")
        assert isinstance(motivo, str)
        assert motivo


def test_trace_do_prim_nao_altera_arestas_nem_custo(grafo_classico):
    sem_trace = prim(grafo_classico, trace=False)
    com_trace = prim(grafo_classico, trace=True)

    assert sem_trace.trace is None
    assert com_trace.trace is not None
    assert com_trace.total_cost == pytest.approx(sem_trace.total_cost)
    assert conjunto_de_arestas(com_trace) == conjunto_de_arestas(sem_trace)
    assert com_trace.n_components == sem_trace.n_components


def test_trace_do_prim_emite_eventos_essenciais(grafo_classico):
    resultado = prim(grafo_classico, trace=True)
    eventos = list(resultado.trace)

    assert eventos
    tipos = [tipo_evento(evento) for evento in eventos]
    assert set(tipos) <= TIPOS_PRIM
    assert tipos[0] == "start"
    assert {"start", "push", "pop", "accept"} <= set(tipos)


def test_trace_do_prim_indica_reinicio_em_grafo_desconexo(grafo_desconexo):
    resultado = prim(grafo_desconexo, trace=True)

    eventos = list(resultado.trace)
    tipos = [tipo_evento(evento) for evento in eventos]

    assert eventos
    assert set(tipos) <= TIPOS_PRIM
    assert tipos[0] == "start"
    assert "restart" in tipos


@pytest.mark.parametrize(
    ("n", "extras", "seed", "pesos_negativos"),
    [
        (4, 2, 101, False),
        (7, 10, 202, False),
        (12, 25, 303, False),
        (25, 70, 404, False),
        (40, 120, 505, False),
        (10, 20, 606, True),
    ],
    ids=[
        "n4",
        "n7",
        "n12",
        "n25",
        "n40",
        "n10-com-negativos",
    ],
)
def test_custo_igual_ao_networkx_em_grafos_aleatorios(
    n, extras, seed, pesos_negativos
):
    grafo, grafo_nx = gerar_grafo_conexo(
        n, extras, seed, pesos_negativos=pesos_negativos
    )

    resultado_kruskal = kruskal(grafo)
    resultado_prim = prim(grafo)
    custo_esperado = custo_mst_networkx(grafo_nx)

    assert resultado_kruskal.total_cost == pytest.approx(
        custo_esperado, abs=1e-9
    )
    assert resultado_prim.total_cost == pytest.approx(custo_esperado, abs=1e-9)
    assert resultado_kruskal.total_cost == pytest.approx(
        resultado_prim.total_cost, abs=1e-9
    )

    for resultado in (resultado_kruskal, resultado_prim):
        assert len(resultado.edges) == n - 1
        assert resultado.n_components == 1
        assert resultado.is_forest is True
        verificacao = verify_forest(grafo, resultado)
        assert verificacao.is_valid is True
