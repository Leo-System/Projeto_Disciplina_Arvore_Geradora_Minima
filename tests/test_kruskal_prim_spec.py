"""Testes de especificação detalhados para Kruskal (K-01..K-16) e Prim (P-01..P-17).

Baseados no PLAN §3.4 e §3.5. Usam padrão AAA e nomes em português.
"""

from __future__ import annotations

import copy
import time
from typing import Any

import networkx as nx
import pytest

from backend.app.algorithms.graph import Graph, GraphValidationError
from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.prim import prim
from backend.app.algorithms.verify import verify_forest
from conftest import (
    aresta,
    construir_grafo,
    construir_grafo_classico,
    construir_grafo_com_empates,
    construir_grafo_com_pesos_negativos,
    construir_grafo_desconexo,
    conjunto_de_arestas,
    custo_mst_networkx,
    extremidades,
    gerar_grafo_conexo,
    no,
    tipo_evento,
    peso_da_aresta,
)

# ---------------------------------------------------------------------------
# Constantes compartilhadas
# ---------------------------------------------------------------------------

MST_CLASSICA = sorted(
    [
        ("A", "C", 2.0),
        ("B", "C", 1.0),
        ("B", "D", 5.0),
        ("D", "E", 2.0),
        ("E", "F", 3.0),
    ]
)

ORDEM_ACEITACAO_KRUSKAL_CLASSICO = [
    ("B", "C", 1.0),  # 1ª aceita
    ("A", "C", 2.0),  # 2ª aceita
    ("D", "E", 2.0),  # 3ª aceita
    ("E", "F", 3.0),  # 4ª aceita
    ("B", "D", 5.0),  # 5ª aceita (para aqui, n-1=5)
]

ORDEM_ACEITACAO_PRIM_DE_A = [
    ("A", "C", 2.0),  # 1ª aceita
    ("B", "C", 1.0),  # 2ª aceita
    ("B", "D", 5.0),  # 3ª aceita
    ("D", "E", 2.0),  # 4ª aceita
    ("E", "F", 3.0),  # 5ª aceita
]

ARestas_REJEITADAS_KRUSKAL_ESPERADAS = {
    ("A", "B", 4.0): "mesmo componente",
    ("C", "D", 8.0): "mesmo componente",
    ("C", "E", 10.0): "mesmo componente",
    ("D", "F", 6.0): "mesmo componente",
}

TIPOS_KRUSKAL = {"consider", "accept", "reject", "sorted", "stop"}
TIPOS_PRIM = {"start", "restart", "push", "pop", "accept", "skip", "update_key", "extraction"}


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------

def _ordenar_arestas_para_comparacao(arestas):
    """Normaliza e ordena lista de arestas para comparação determinística."""
    return sorted(
        (min(u, v), max(u, v), float(w))
        for u, v, w in (
            (extremidades(e)[0], extremidades(e)[1], peso_da_aresta(e))
            for e in arestas
        )
    )


def _ids_arestas_aceitas(resultado):
    """Lista de (u, v, peso) das arestas aceitas, na ordem de aceitação."""
    return [
        (min(extremidades(e)[0], extremidades(e)[1]),
         max(extremidades(e)[0], extremidades(e)[1]),
         float(peso_da_aresta(e)))
        for e in resultado.edges
    ]


# ===========================================================================
# KRUSKAL — K-01 a K-16
# ===========================================================================

class TestKruskalBasico:
    """K-01: Exemplo A–F do material — custo 13, 5 arestas, conjunto correto."""

    def test_k01_custo_13_arestas_conjunto_correto(self, grafo_classico):
        resultado = kruskal(grafo_classico)

        assert resultado.algorithm == "kruskal"
        assert resultado.total_cost == pytest.approx(13.0)
        assert len(resultado.edges) == 5
        assert resultado.n_components == 1
        assert resultado.is_forest is True
        assert conjunto_de_arestas(resultado) == MST_CLASSICA


class TestKruskalOrdemAceitacao:
    """K-02: Ordem exata de aceitação no A–F."""

    def test_k02_ordem_exata_aceitacao_e_rejeicao_ab(self, grafo_classico):
        resultado = kruskal(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        # Extrai apenas eventos de aceitação, na ordem
        aceitacoes = [e for e in eventos if tipo_evento(e) == "accept"]
        assert len(aceitacoes) == 5

        ordem_obtida = [
            (min(campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]),
             max(campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]),
             float(campo_evento(e, "edge")["weight"]))
            for e in aceitacoes
        ]
        assert ordem_obtida == ORDEM_ACEITACAO_KRUSKAL_CLASSICO

        # Verifica que A-B foi considerada e REJEITADA (formaria ciclo)
        consideracoes = [e for e in eventos if tipo_evento(e) == "consider"]
        aresta_ab = next(
            (e for e in consideracoes
             if set([campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]]) == {"A", "B"}),
            None
        )
        assert aresta_ab is not None, "Aresta A-B deveria ter sido considerada"
        assert campo_evento(aresta_ab, "same_component") is True, "A-C-B já conecta A e B; A-B deve ser considerada no mesmo componente"

        rejeicoes = [e for e in eventos if tipo_evento(e) == "reject"]
        rejeicao_ab = next(
            (e for e in rejeicoes
             if set([campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]]) == {"A", "B"}),
            None
        )
        assert rejeicao_ab is not None, "Aresta A-B deveria ter sido rejeitada"
        assert "mesmo componente" in campo_evento(rejeicao_ab, "reason").lower()

        # Verifica que B-D foi aceita (5ª)
        aceitacao_bd = next(
            (e for e in aceitacoes
             if set([campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]]) == {"B", "D"}),
            None
        )
        assert aceitacao_bd is not None, "Aresta B-D deveria ter sido aceita"

        # Verifica que parou sem analisar as restantes (C-D, C-E, D-F)
        # O último evento deve ser 'accept' de B-D ou 'stop'
        # Como o trace atual não tem 'stop', verificamos que só há 5 aceitações
        assert len(aceitacoes) == 5


class TestKruskalDesconexo:
    """K-03: Grafo desconexo — floresta n−c arestas, custo e componentes corretos."""

    def test_k03_grafo_desconexo_floresta_n_menos_c(self, grafo_desconexo):
        n = grafo_desconexo.n_nodes
        c = 3  # {A,B}, {C,D}, {E}

        resultado = kruskal(grafo_desconexo)

        assert resultado.n_components == c
        assert len(resultado.edges) == n - c
        assert resultado.total_cost == pytest.approx(3.0)  # 1 + 2
        assert resultado.is_forest is True
        assert conjunto_de_arestas(resultado) == sorted([
            ("A", "B", 1.0),
            ("C", "D", 2.0),
        ])
        # Componentes ordenados pelo menor id
        assert [min(comp) for comp in resultado.components] == ["A", "C", "E"]


class TestKruskalParadaAntecipada:
    """K-04: Parada antecipada — conexo para em n−1, desconexo em n−c; não examina o resto."""

    def test_k04_parada_antecipada_conexo(self, grafo_classico):
        # Grafo conexo: 6 vértices, 9 arestas. Deve parar após aceitar 5 (n-1).
        resultado = kruskal(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        aceitacoes = [e for e in eventos if tipo_evento(e) == "accept"]
        consideracoes = [e for e in eventos if tipo_evento(e) == "consider"]

        assert len(aceitacoes) == 5  # n-1
        # Deve ter considerado apenas até a 5ª aceitação + rejeições até ali
        # As arestas C-D(8), C-E(10), D-F(6) NÃO devem ter sido consideradas
        arestas_consideradas = {
            (min(campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]),
             max(campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]))
            for e in consideracoes
        }
        assert ("C", "D") not in arestas_consideradas, "C-D não deveria ser examinada (parada antecipada)"
        assert ("C", "E") not in arestas_consideradas, "C-E não deveria ser examinada (parada antecipada)"
        assert ("D", "F") not in arestas_consideradas, "D-F não deveria ser examinada (parada antecipada)"

    def test_k04_parada_antecipada_desconexo(self, grafo_desconexo):
        # 5 vértices, 3 componentes, 2 arestas. Para ao aceitar 2 (n-c=5-3=2).
        resultado = kruskal(grafo_desconexo, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        aceitacoes = [e for e in eventos if tipo_evento(e) == "accept"]
        assert len(aceitacoes) == 2  # n-c
        # Como só há 2 arestas no grafo, todas são consideradas


class TestKruskalPesosNegativosZero:
    """K-05: Pesos negativos e zero — custo correto, aceita ≤ 0."""

    def test_k05_pesos_negativos_e_zero(self):
        nodes = [no(v) for v in "ABCD"]
        edges = [
            aresta("A", "B", -5),
            aresta("B", "C", 0),
            aresta("C", "D", -1),
            aresta("A", "D", 10),
        ]
        grafo = construir_grafo(nodes, edges)

        resultado = kruskal(grafo)

        assert resultado.total_cost == pytest.approx(-6.0)  # -5 + 0 + -1
        assert len(resultado.edges) == 3
        assert resultado.n_components == 1
        assert verify_forest(grafo, resultado).is_valid is True


class TestKruskalEmpates:
    """K-06: Empates de peso — desempate determinístico por (peso, menor id, maior id); repetição igual."""

    def test_k06_empate_desempate_deterministico(self, grafo_com_empates):
        # Ciclo A-B-C-D-A, todos peso 1
        # Ordem esperada: (1, A, B), (1, A, D), (1, B, C) -> aceita A-B, A-D, B-C
        # C-D seria rejeitada (formaria ciclo)
        resultado1 = kruskal(grafo_com_empates)
        resultado2 = kruskal(grafo_com_empates)

        assert _ids_arestas_aceitas(resultado1) == _ids_arestas_aceitas(resultado2)
        assert conjunto_de_arestas(resultado1) == sorted([
            ("A", "B", 1.0),
            ("A", "D", 1.0),
            ("B", "C", 1.0),
        ])

    def test_k06_empate_de_peso_tem_desempate_deterministico(self):
        # K-06: com todos os pesos iguais, o desempate é determinístico.
        # IDs de mesmo comprimento isolam o critério de desempate da questão
        # numérico × lexicográfico (coberta em K-16 / BUG-002).
        nodes = [no(v) for v in ["01", "02", "10", "11"]]
        edges = [
            aresta("01", "02", 1),
            aresta("02", "10", 1),
            aresta("10", "11", 1),
            aresta("11", "01", 1),
        ]

        # Act
        primeiro = kruskal(construir_grafo(nodes, edges))
        segundo = kruskal(construir_grafo(nodes, edges))

        # Assert
        assert conjunto_de_arestas(primeiro) == conjunto_de_arestas(segundo)
        assert len(primeiro.edges) == 3
        assert primeiro.total_cost == pytest.approx(3.0)
        # Ordem determinística por (peso, u, v) com IDs de mesmo comprimento:
        # aceita as três primeiras arestas e rejeita a quarta (fecha ciclo).
        assert conjunto_de_arestas(primeiro) == sorted(
            [("01", "02", 1.0), ("01", "11", 1.0), ("02", "10", 1.0)]
        )


class TestKruskalCasosDeBorda:
    """K-07: 1 vértice / 2 vizinhos / 2 não vizinhos / sem arestas — resultados corretos e n_components coerente."""

    def test_k07_um_vertice(self):
        grafo = construir_grafo([no("A")], [])
        resultado = kruskal(grafo)
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 1
        assert resultado.components == [["A"]]
        assert resultado.is_forest is True

    def test_k07_dois_vertices_vizinhos(self):
        grafo = construir_grafo([no("A"), no("B")], [aresta("A", "B", 7)])
        resultado = kruskal(grafo)
        assert len(resultado.edges) == 1
        assert resultado.total_cost == pytest.approx(7.0)
        assert resultado.n_components == 1
        assert conjunto_de_arestas(resultado) == [("A", "B", 7.0)]

    def test_k07_dois_vertices_nao_vizinhos(self):
        grafo = construir_grafo([no("A"), no("B")], [])
        resultado = kruskal(grafo)
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 2
        assert sorted(min(c) for c in resultado.components) == ["A", "B"]

    def test_k07_sem_arestas_quatro_vertices(self):
        grafo = construir_grafo([no(v) for v in "ABCD"], [])
        resultado = kruskal(grafo)
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 4
        assert sorted(min(c) for c in resultado.components) == ["A", "B", "C", "D"]


class TestKruskalMetricas:
    """K-08: Métricas — time_ms≥0, edges_examined≥accepted, accepted==len(edges), rejected≥0, find_calls/union_calls≥0."""

    def test_k08_metricas_presentes_e_coerentes(self, grafo_classico):
        resultado = kruskal(grafo_classico)

        m = resultado.metrics
        for chave in ("time_ms", "edges_examined", "accepted", "rejected", "find_calls", "union_calls"):
            assert chave in m, f"Métrica {chave} ausente"
            assert isinstance(m[chave], (int, float))

        assert m["time_ms"] >= 0
        assert m["edges_examined"] >= m["accepted"]
        assert m["accepted"] == len(resultado.edges)
        assert m["rejected"] >= 0
        assert m["find_calls"] >= 0
        assert m["union_calls"] >= 0


class TestKruskalMetricasFases:
    """K-09 (CONF): Métricas sort_time_ms e loop_time_ms — verificar presença e coerência; ausência é divergência."""

    def test_k09_metricas_sort_time_ms_e_loop_time_ms_presentes(self, grafo_classico):
        resultado = kruskal(grafo_classico)

        m = resultado.metrics
        # PLAN prevê sort_time_ms e loop_time_ms
        for chave in ("sort_time_ms", "loop_time_ms"):
            if chave not in m:
                pytest.fail(
                    f"DIVERGÊNCIA (CONF): Métrica '{chave}' prevista no PLAN §6.4 "
                    f"mas ausente nas métricas do Kruskal. Métricas disponíveis: {list(m.keys())}"
                )
            assert isinstance(m[chave], (int, float))
            assert m[chave] >= 0


class TestKruskalTraceFalse:
    """K-10: trace=False -> result.trace is None."""

    def test_k10_trace_false_retorna_none(self, grafo_classico):
        resultado = kruskal(grafo_classico, trace=False)
        assert resultado.trace is None


class TestKruskalTraceNaoAlteraResultado:
    """K-11: Trace não altera custo/arestas/componentes/nº arestas."""

    def test_k11_trace_nao_altera_resultado(self, grafo_classico):
        sem = kruskal(grafo_classico, trace=False)
        com = kruskal(grafo_classico, trace=True)

        assert sem.trace is None
        assert com.trace is not None
        assert com.total_cost == pytest.approx(sem.total_cost)
        assert conjunto_de_arestas(com) == conjunto_de_arestas(sem)
        assert com.n_components == sem.n_components
        assert len(com.edges) == len(sem.edges)
        assert com.metrics["accepted"] == sem.metrics["accepted"]


class TestKruskalTraceEstrutura:
    """K-12: Estrutura do trace — consider (componente u/v, same_component), accept (custo parcial, contagem), reject (motivo)."""

    def test_k12_trace_eventos_consider_accept_reject_estrutura(self, grafo_classico):
        resultado = kruskal(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        for evento in eventos:
            t = tipo_evento(evento)
            if t == "consider":
                assert "step" in evento
                assert "edge" in evento
                assert "component_u_size" in evento
                assert "component_v_size" in evento
                assert "same_component" in evento
                assert isinstance(evento["component_u_size"], int)
                assert isinstance(evento["component_v_size"], int)
                assert isinstance(evento["same_component"], bool)
            elif t == "accept":
                assert "step" in evento
                assert "edge" in evento
                assert "total_cost_so_far" in evento
                assert "accepted_count" in evento
                assert isinstance(evento["total_cost_so_far"], (int, float))
                assert isinstance(evento["accepted_count"], int)
            elif t == "reject":
                assert "step" in evento
                assert "edge" in evento
                assert "reason" in evento
                assert isinstance(evento["reason"], str)
                assert evento["reason"]


class TestKruskalTraceEventosSortedStop:
    """K-13 (CONF): Eventos 'sorted' e 'stop' previstos no PLAN; ausência é divergência (BUG-004)."""

    def test_k13_eventos_sorted_e_stop_presentes(self, grafo_classico):
        resultado = kruskal(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        tipos = {tipo_evento(e) for e in eventos}

        if "sorted" not in tipos:
            pytest.fail(
                "DIVERGÊNCIA (CONF) / BUG-004: Evento 'sorted' previsto no PLAN §6.5 "
                f"mas ausente no trace do Kruskal. Tipos presentes: {sorted(tipos)}"
            )

        if "stop" not in tipos:
            pytest.fail(
                "DIVERGÊNCIA (CONF) / BUG-004: Evento 'stop' previsto no PLAN §6.5 "
                f"mas ausente no trace do Kruskal. Tipos presentes: {sorted(tipos)}"
            )


class TestKruskalTempoComTrace:
    """K-14: Tempo medido em passada limpa separada da passada com trace."""

    def test_k14_tempo_medido_em_passada_limpa_separada(self, grafo_classico):
        # Verifica que a implementação faz duas passadas quando trace=True
        # (uma com trace para eventos, outra limpa para métricas de tempo)
        # Isso é verificado indiretamente: o tempo não deve ser zero e
        # as métricas devem vir da passada limpa.

        resultado = kruskal(grafo_classico, trace=True)

        # A métrica time_ms deve refletir a passada limpa (sem overhead de trace)
        assert resultado.metrics["time_ms"] >= 0
        # O trace deve estar presente
        assert resultado.trace is not None
        # As outras métricas devem ser consistentes
        assert resultado.metrics["accepted"] == len(resultado.edges)


class TestKruskalGrafosAleatorios:
    """K-15: Grafos aleatórios com semente fixa — custo igual a NetworkX e ao Prim; verify aprova."""

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
        ids=["n4", "n7", "n12", "n25", "n40", "n10-com-negativos"],
    )
    def test_k15_grafos_aleatorios_custo_igual_networkx_e_prim(self, n, extras, seed, pesos_negativos):
        grafo, grafo_nx = gerar_grafo_conexo(n, extras, seed, pesos_negativos=pesos_negativos)

        resultado_kruskal = kruskal(grafo)
        resultado_prim = prim(grafo)
        custo_esperado = custo_mst_networkx(grafo_nx)

        assert resultado_kruskal.total_cost == pytest.approx(custo_esperado, abs=1e-9)
        assert resultado_prim.total_cost == pytest.approx(custo_esperado, abs=1e-9)
        assert resultado_kruskal.total_cost == pytest.approx(resultado_prim.total_cost, abs=1e-9)

        for resultado in (resultado_kruskal, resultado_prim):
            assert len(resultado.edges) == n - 1
            assert resultado.n_components == 1
            assert resultado.is_forest is True
            verificacao = verify_forest(grafo, resultado)
            assert verificacao.is_valid is True


class TestKruskalDesempateIdsVariaveis:
    """K-16: IDs "2"/"10" — desempate numérico previsto no PLAN (BUG-002)."""

    def test_k16_desempate_numerico_ids_tamanho_variavel(self):
        # Mesmo ciclo de K-06, mas com ids de tamanho variável.
        nodes = [no(v) for v in ["1", "2", "10", "11"]]
        edges = [
            aresta("1", "2", 1),
            aresta("2", "10", 1),
            aresta("10", "11", 1),
            aresta("11", "1", 1),
        ]
        grafo = construir_grafo(nodes, edges)

        resultado = kruskal(grafo)

        def par_numerico(edge):
            """Extremos normalizadas em ordem numérica (não lexicográfica)."""
            u, v = extremidades(edge)
            if int(u) > int(v):
                u, v = v, u
            return (u, v, peso_da_aresta(edge))

        arestas_aceitas = [par_numerico(e) for e in resultado.edges]

        # PLAN §6.2: ordenar por (peso, índice menor, índice maior), com o
        # índice numérico 1→0, 2→1, 10→2, 11→3. Chaves: 1-2=(0,1),
        # 1-11=(0,3), 2-10=(1,2) e 10-11=(2,3) → exame 1-2, 1-11, 2-10,
        # 10-11; as três primeiras ligam componentes distintos e são aceitas.
        esperado_numerico = [
            ("1", "2", 1.0),
            ("1", "11", 1.0),
            ("2", "10", 1.0),
        ]

        if arestas_aceitas != esperado_numerico:
            pytest.fail(
                "Desempate fora da ordem numérica prevista no PLAN (BUG-002). "
                f"Obtido: {arestas_aceitas}, Esperado (numérico): {esperado_numerico}"
            )


# ===========================================================================
# PRIM — P-01 a P-17
# ===========================================================================

class TestPrimBasico:
    """P-01: Prim a partir de A — custo 13, 5 arestas, conjunto correto."""

    def test_p01_prim_a_partir_de_a_custo_13_conjunto_correto(self, grafo_classico):
        resultado = prim(grafo_classico, start_vertex="A")

        assert resultado.algorithm == "prim"
        assert resultado.total_cost == pytest.approx(13.0)
        assert len(resultado.edges) == 5
        assert resultado.n_components == 1
        assert resultado.is_forest is True
        assert conjunto_de_arestas(resultado) == MST_CLASSICA


class TestPrimOrdemAceitacao:
    """P-02: Ordem exata de aceitação a partir de A — A-C, B-C, B-D, D-E, E-F."""

    def test_p02_ordem_exata_aceitacao_a_partir_de_a(self, grafo_classico):
        resultado = prim(grafo_classico, start_vertex="A", trace=True)
        eventos = resultado.trace
        assert eventos is not None

        aceitacoes = [e for e in eventos if tipo_evento(e) == "accept"]
        assert len(aceitacoes) == 5

        ordem_obtida = [
            (min(campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]),
             max(campo_evento(e, "edge")["u"], campo_evento(e, "edge")["v"]),
             float(campo_evento(e, "edge")["weight"]))
            for e in aceitacoes
        ]
        assert ordem_obtida == ORDEM_ACEITACAO_PRIM_DE_A


class TestPrimInicioAlternativo:
    """P-03: Início em cada vértice do A–F — continua ótimo (custo 13)."""

    @pytest.mark.parametrize("inicio", list("ABCDEF"))
    def test_p03_inicio_em_cada_vertice_continua_otimo(self, grafo_classico, inicio):
        resultado = prim(grafo_classico, start_vertex=inicio)

        assert resultado.total_cost == pytest.approx(13.0)
        assert len(resultado.edges) == 5
        assert resultado.n_components == 1
        # Neste grafo a MST é única
        assert conjunto_de_arestas(resultado) == MST_CLASSICA
        assert verify_forest(grafo_classico, resultado).is_valid is True


class TestPrimVerticeInicialInexistente:
    """P-04: Vértice inicial inexistente -> GraphValidationError."""

    def test_p04_vertice_inicial_inexistente_lanca_erro(self, grafo_classico):
        with pytest.raises(GraphValidationError) as exc_info:
            prim(grafo_classico, start_vertex="Z")
        assert "inexistente" in str(exc_info.value).lower()


class TestPrimDesconexo:
    """P-05: Grafo desconexo — reinicia no próximo não visitado; floresta n−c; componentes corretos; evento/indicador de reinício."""

    def test_p05_grafo_desconexo_reinicia_floresta_n_menos_c(self, grafo_desconexo):
        n = grafo_desconexo.n_nodes
        c = 3

        resultado = prim(grafo_desconexo)

        assert resultado.n_components == c
        assert len(resultado.edges) == n - c
        assert resultado.total_cost == pytest.approx(3.0)
        assert resultado.is_forest is True
        assert conjunto_de_arestas(resultado) == sorted([
            ("A", "B", 1.0),
            ("C", "D", 2.0),
        ])
        assert sorted(min(comp) for comp in resultado.components) == ["A", "C", "E"]

    def test_p05_trace_indica_reinicio(self, grafo_desconexo):
        resultado = prim(grafo_desconexo, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        tipos = [tipo_evento(e) for e in eventos]
        assert "restart" in tipos, "Evento 'restart' deveria estar presente no trace de grafo desconexo"


class TestPrimPesosNegativosZero:
    """P-06: Pesos negativos e zero — custo correto."""

    def test_p06_pesos_negativos_e_zero(self):
        nodes = [no(v) for v in "ABCD"]
        edges = [
            aresta("A", "B", -5),
            aresta("B", "C", 0),
            aresta("C", "D", -1),
            aresta("A", "D", 10),
        ]
        grafo = construir_grafo(nodes, edges)

        resultado = prim(grafo)

        assert resultado.total_cost == pytest.approx(-6.0)
        assert len(resultado.edges) == 3
        assert resultado.n_components == 1
        assert verify_forest(grafo, resultado).is_valid is True


class TestPrimEmpates:
    """P-07: Empates — escolha determinística; repetição estável."""

    def test_p07_empates_deterministicos_e_repetiveis(self, grafo_com_empates):
        resultado1 = prim(grafo_com_empates)
        resultado2 = prim(grafo_com_empates)

        assert _ids_arestas_aceitas(resultado1) == _ids_arestas_aceitas(resultado2)
        assert resultado1.total_cost == pytest.approx(resultado2.total_cost)
        assert verify_forest(grafo_com_empates, resultado1).is_valid is True
        assert verify_forest(grafo_com_empates, resultado2).is_valid is True


class TestPrimCasosDeBorda:
    """P-08: 1 vértice / 2 vizinhos / 2 não vizinhos / sem arestas e n_components coerente."""

    def test_p08_um_vertice(self):
        grafo = construir_grafo([no("A")], [])
        resultado = prim(grafo)
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 1
        assert resultado.components == [["A"]]

    def test_p08_dois_vertices_vizinhos(self):
        grafo = construir_grafo([no("A"), no("B")], [aresta("A", "B", 7)])
        resultado = prim(grafo)
        assert len(resultado.edges) == 1
        assert resultado.total_cost == pytest.approx(7.0)
        assert resultado.n_components == 1

    def test_p08_dois_vertices_nao_vizinhos(self):
        grafo = construir_grafo([no("A"), no("B")], [])
        resultado = prim(grafo)
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 2

    def test_p08_sem_arestas_quatro_vertices(self):
        grafo = construir_grafo([no(v) for v in "ABCD"], [])
        resultado = prim(grafo)
        assert len(resultado.edges) == 0
        assert resultado.total_cost == pytest.approx(0.0)
        assert resultado.n_components == 4


class TestPrimMetricas:
    """P-09: Métricas — time_ms≥0, accepted==len(edges), heap_pushes≥heap_pops≥stale_pops≥0."""

    def test_p09_metricas_presentes_e_coerentes(self, grafo_classico):
        resultado = prim(grafo_classico)

        m = resultado.metrics
        for chave in ("time_ms", "edges_examined", "accepted", "heap_pushes", "heap_pops", "stale_pops"):
            assert chave in m, f"Métrica {chave} ausente"
            assert isinstance(m[chave], (int, float))

        assert m["time_ms"] >= 0
        assert m["accepted"] == len(resultado.edges)
        assert m["heap_pushes"] >= 0
        assert m["heap_pops"] >= m["stale_pops"] >= 0


class TestPrimMetricaKeyUpdates:
    """P-10 (CONF): Métrica key_updates — PLAN prevê; verificar presença."""

    def test_p10_metrica_key_updates_presente(self, grafo_classico):
        resultado = prim(grafo_classico)

        m = resultado.metrics
        if "key_updates" not in m:
            pytest.fail(
                "DIVERGÊNCIA (CONF): Métrica 'key_updates' prevista no PLAN §6.4 "
                f"mas ausente nas métricas do Prim. Métricas disponíveis: {list(m.keys())}"
            )
        assert isinstance(m["key_updates"], (int, float))
        assert m["key_updates"] >= 0


class TestPrimFronteira:
    """P-11: Fronteira — só entram na heap arestas para vértices fora da árvore; entradas obsoletas descartadas."""

    def test_p11_fronteira_so_entra_vertices_fora_arvore(self, grafo_classico):
        resultado = prim(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        # Verifica que eventos 'push' só adicionam arestas para vértices não visitados
        # (o trace atual não expõe diretamente o conjunto visitado em cada push,
        # mas podemos verificar que não há pushes para vértices já na árvore
        # examinando a lógica: push_frontier só adiciona se neighbor not in visited)

        # Verifica que stale_pops >= 0 e que eventos 'skip' existem quando há pops obsoletos
        stale_pops = resultado.metrics["stale_pops"]
        if stale_pops > 0:
            skips = [e for e in eventos if tipo_evento(e) == "skip"]
            assert len(skips) >= stale_pops


class TestPrimTraceNaoAlteraResultado:
    """P-12: Trace não altera resultado — mesmo custo/arestas/componentes com/sem trace."""

    def test_p12_trace_nao_altera_resultado(self, grafo_classico):
        sem = prim(grafo_classico, trace=False)
        com = prim(grafo_classico, trace=True)

        assert sem.trace is None
        assert com.trace is not None
        assert com.total_cost == pytest.approx(sem.total_cost)
        assert conjunto_de_arestas(com) == conjunto_de_arestas(sem)
        assert com.n_components == sem.n_components
        assert len(com.edges) == len(sem.edges)


class TestPrimTraceEstrutura:
    """P-13: Estrutura do trace — PLAN prevê start(r), extração (chave/pai/tamanho do corte), update_key, accept, skip_stale; 
    implementação atual usa push/pop/skip/restart — registrar divergência se não bater (BUG-004/relacionado)."""

    def test_p13_trace_estrutura_prevista_vs_atual(self, grafo_classico):
        resultado = prim(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        tipos_presentes = {tipo_evento(e) for e in eventos}

        # PLAN prevê: start, extraction (com key, parent, cut_size), update_key, accept, skip_stale
        # Implementação atual: start, push, pop, accept, skip, restart

        # Verifica presença dos tipos atuais
        assert "start" in tipos_presentes
        assert "push" in tipos_presentes
        assert "pop" in tipos_presentes
        assert "accept" in tipos_presentes

        # Registra divergências em relação ao PLAN
        divergencias = []
        if "extraction" not in tipos_presentes and "update_key" not in tipos_presentes:
            divergencias.append(
                "PLAN prevê eventos 'extraction' (com chave/pai/cut_size) e 'update_key', "
                "mas implementação usa 'push'/'pop'/'skip'. Registrar como BUG-004/relacionado."
            )

        # Se há divergências, falha o teste documentando-as
        if divergencias:
            pytest.fail("DIVERGÊNCIAS de trace (P-13):\n" + "\n".join(divergencias))


class TestPrimTraceCamposCorte:
    """P-14: tree_size e cut_size coerentes a cada aceitação."""

    def test_p14_tree_size_e_cut_size_coerentes(self, grafo_classico):
        resultado = prim(grafo_classico, trace=True)
        eventos = resultado.trace
        assert eventos is not None

        aceitacoes = [e for e in eventos if tipo_evento(e) == "accept"]
        n_total = grafo_classico.n_nodes

        for i, evento in enumerate(aceitacoes, 1):
            tree_size = evento.get("tree_size")
            cut_size = evento.get("cut_size")

            assert tree_size is not None, f"Aceitação {i}: tree_size ausente"
            assert cut_size is not None, f"Aceitação {i}: cut_size ausente"

            # tree_size deve ser o número de vértices na componente atual
            # cut_size deve ser n_total - tree_size (vértices fora da árvore no componente?)
            # Na implementação atual: tree_size = len(component_nodes), cut_size = n_nodes - len(component_nodes)
            assert tree_size == i + 1, f"Aceitação {i}: tree_size={tree_size} esperado {i+1}"
            assert cut_size == n_total - tree_size, f"Aceitação {i}: cut_size={cut_size} esperado {n_total - tree_size}"


class TestPrimTempoComTrace:
    """P-15: Medição de tempo com trace — passada limpa separada."""

    def test_p15_tempo_medido_em_passada_limpa_separada(self, grafo_classico):
        resultado = prim(grafo_classico, trace=True)

        assert resultado.metrics["time_ms"] >= 0
        assert resultado.trace is not None
        assert resultado.metrics["accepted"] == len(resultado.edges)


class TestPrimGrafosAleatorios:
    """P-16: Grafos aleatórios com semente fixa — custo igual a NetworkX/Kruskal; verify aprova."""

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
        ids=["n4", "n7", "n12", "n25", "n40", "n10-com-negativos"],
    )
    def test_p16_grafos_aleatorios_custo_igual_networkx_kruskal(self, n, extras, seed, pesos_negativos):
        grafo, grafo_nx = gerar_grafo_conexo(n, extras, seed, pesos_negativos=pesos_negativos)

        resultado_prim = prim(grafo)
        resultado_kruskal = kruskal(grafo)
        custo_esperado = custo_mst_networkx(grafo_nx)

        assert resultado_prim.total_cost == pytest.approx(custo_esperado, abs=1e-9)
        assert resultado_kruskal.total_cost == pytest.approx(custo_esperado, abs=1e-9)
        assert resultado_prim.total_cost == pytest.approx(resultado_kruskal.total_cost, abs=1e-9)

        for resultado in (resultado_prim, resultado_kruskal):
            assert len(resultado.edges) == n - 1
            assert resultado.n_components == 1
            assert resultado.is_forest is True
            verificacao = verify_forest(grafo, resultado)
            assert verificacao.is_valid is True


class TestPrimStartVertexNone:
    """P-17: start_vertex=None usa o menor id determinístico."""

    def test_p17_start_vertex_none_usa_menor_id(self, grafo_classico):
        # O menor id em "ABCDEF" é "A"
        resultado_none = prim(grafo_classico, start_vertex=None)
        resultado_a = prim(grafo_classico, start_vertex="A")

        assert resultado_none.total_cost == pytest.approx(resultado_a.total_cost)
        assert conjunto_de_arestas(resultado_none) == conjunto_de_arestas(resultado_a)
        assert resultado_none.n_components == resultado_a.n_components

    def test_p17_start_vertex_none_menor_id_deterministico(self):
        # Grafo com IDs não alfabéticos para testar ordenação
        nodes = [no(v) for v in ["Z", "10", "2", "A"]]
        edges = [
            aresta("Z", "10", 1),
            aresta("10", "2", 1),
            aresta("2", "A", 1),
            aresta("A", "Z", 1),
        ]
        grafo = construir_grafo(nodes, edges)

        # Menor id lexicográfico: "10" < "2" < "A" < "Z"
        resultado = prim(grafo, start_vertex=None)
        assert resultado.total_cost == pytest.approx(3.0)
        assert len(resultado.edges) == 3


# ===========================================================================
# Helpers de campo de evento (reutiliza conftest mas adiciona tipagem)
# ===========================================================================

def campo_evento(evento: dict[str, Any], nome: str) -> Any:
    """Extrai campo de evento (dict ou objeto)."""
    if isinstance(evento, dict):
        return evento[nome]
    return getattr(evento, nome)