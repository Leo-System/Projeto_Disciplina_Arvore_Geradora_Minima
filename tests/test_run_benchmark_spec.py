"""Testes de especificação: execução/serialização (R-01..R-15) e benchmark (B-01..B-10).

Contratos testados:
- backend/app/services/run_service.py  (run_algorithms, compare_results)
- backend/app/services/serialization.py (graph_stats, graph_to_dict)
- backend/app/services/benchmark.py    (run_benchmark, _measure)

Padrão AAA, nomes em português "deve ... quando ...".
Não há skip/xfail/only: se o código divergir do .sdd/TESTES_PLAN.md, o teste falha.
"""

from __future__ import annotations

from copy import copy
from inspect import signature

import math
import pytest

from backend.app.algorithms.graph import Edge
from backend.app.algorithms.kruskal import kruskal as algoritmo_kruskal
from backend.app.algorithms.prim import prim as algoritmo_prim
from backend.app.algorithms.result import MSTResult
from backend.app.errors import NotFoundError, ValidationError
from backend.app.services import benchmark as modulo_benchmark
from backend.app.services.benchmark import _measure, run_benchmark
from backend.app.services.run_service import compare_results, run_algorithms
from backend.app.services.serialization import graph_stats, graph_to_dict
from conftest import aresta, construir_grafo, construir_grafo_classico, no

ESTATISTAS_ESPERADOS = {
    "n_nodes",
    "n_edges",
    "n_components",
    "is_connected",
    "n_divisa_edges",
    "n_manual_edges",
    "component_sizes",
}

COMPARACAO_CAMPOS_NULOS = (
    "same_cost",
    "same_edges",
    "cost_difference",
    "has_weight_ties",
    "is_consistent",
)


def _grafo_pesos_distintos():
    """Grafo A-B-C-D com todos os pesos diferentes: MST é única."""
    return construir_grafo(
        [no(v) for v in "ABCD"],
        [
            aresta("A", "B", 1),
            aresta("B", "C", 2),
            aresta("C", "D", 3),
            aresta("D", "A", 4),
            aresta("A", "C", 5),
        ],
    )


def _fabrica_resultado(algorithm, arestas, total_cost, nodes=None):
    """Cria MSTResult com arestas e custo escolhidos (isola compare_results)."""
    if nodes is None:
        nodes = sorted({vertice for u, v, _ in arestas for vertice in (u, v)})
    return MSTResult(
        algorithm=algorithm,
        edges=[Edge(u, v, float(w)) for u, v, w in arestas],
        total_cost=float(total_cost),
        n_components=1,
        components=[sorted(nodes)],
        is_forest=True,
    )


def _pares(arestas_dicts):
    return {(min(d["u"], d["v"]), max(d["u"], d["v"])) for d in arestas_dicts}


# ---------------------------------------------------------------------------
# R-01..R-15: execução e serialização
# ---------------------------------------------------------------------------


def test_run_algorithms_ambos_devolve_kruskal_prim_comparacao_verificacao_e_stats(
    grafo_classico,
):
    # Arrange
    grafo = grafo_classico

    # Act
    resposta = run_algorithms(grafo, algorithm="both")

    # Assert
    assert resposta["kruskal"] is not None
    assert resposta["kruskal"]["algorithm"] == "kruskal"
    assert resposta["prim"] is not None
    assert resposta["prim"]["algorithm"] == "prim"
    comparacao = resposta["comparison"]
    assert set(comparacao) >= {
        "same_cost",
        "same_edges",
        "cost_difference",
        "has_weight_ties",
        "kruskal_only_edges",
        "prim_only_edges",
        "is_consistent",
        "message",
    }
    assert resposta["verification"] is not None
    assert resposta["verification"]["kruskal"]["performed"] is True
    assert resposta["verification"]["prim"]["performed"] is True
    estatisticas = resposta["graph_stats"]
    assert set(estatisticas) == ESTATISTAS_ESPERADOS


def test_run_apenas_kruskal_devolve_prim_none_e_comparacao_avisa_que_falta_um(
    grafo_classico,
):
    # Arrange
    grafo = grafo_classico

    # Act
    resposta = run_algorithms(grafo, algorithm="kruskal")

    # Assert
    assert resposta["kruskal"] is not None
    assert resposta["prim"] is None
    comparacao = resposta["comparison"]
    for campo in COMPARACAO_CAMPOS_NULOS:
        assert comparacao[campo] is None
    assert comparacao["kruskal_only_edges"] == []
    assert comparacao["prim_only_edges"] == []
    assert comparacao["message"] == "Execute os dois algoritmos para ver a comparação completa."


def test_run_apenas_prim_devolve_kruskal_none_e_comparacao_avisa_que_falta_um(
    grafo_classico,
    ):
    # Arrange
    grafo = grafo_classico

    # Act
    resposta = run_algorithms(grafo, algorithm="prim")

    # Assert
    assert resposta["prim"] is not None
    assert resposta["kruskal"] is None
    comparacao = resposta["comparison"]
    for campo in COMPARACAO_CAMPOS_NULOS:
        assert comparacao[campo] is None
    assert comparacao["message"] == "Execute os dois algoritmos para ver a comparação completa."


def test_algoritmo_invalido_gera_validation_error(grafo_classico):
    # Arrange
    grafo = grafo_classico

    # Act + Assert
    with pytest.raises(ValidationError):
        run_algorithms(grafo, algorithm="não-existe")


def test_vertice_inicial_inexistente_gera_validation_error(grafo_classico):
    # Arrange
    grafo = grafo_classico

    # Act + Assert
    with pytest.raises(ValidationError):
        run_algorithms(grafo, algorithm="prim", start_vertex="ZZZ-999")


def test_pesos_distintos_devem_gerar_mesmo_custo_mesmas_arestas_e_consistente():
    # Arrange: pesos todos distintos -> MST única.
    grafo = _grafo_pesos_distintos()

    # Act
    resposta = run_algorithms(grafo, algorithm="both")

    # Assert
    comparacao = resposta["comparison"]
    assert comparacao["has_weight_ties"] is False
    assert comparacao["same_cost"] is True
    assert comparacao["same_edges"] is True
    assert comparacao["is_consistent"] is True
    assert resposta["kruskal"]["total_cost"] == resposta["prim"]["total_cost"]


def test_pesos_com_empates_tem_custo_igual_e_consistente_arestas_podem_diferir(
    grafo_com_empates,
):
    # Arrange
    grafo = grafo_com_empates

    # Act
    resposta = run_algorithms(grafo, algorithm="both")

    # Assert
    comparacao = resposta["comparison"]
    assert comparacao["same_cost"] is True
    assert comparacao["has_weight_ties"] is True
    assert comparacao["is_consistent"] is True
    # same_edges pode ser True ou False em presença de empates: não se afirma.


def test_conjuntos_diferentes_sem_empates_generam_inconsistencia_e_mensagem_de_erro():
    # Arrange: grafo com pesos distintos, mas resultados fabricados com
    # conjuntos diferentes e mesmo custo (situação impossível corretamente).
    grafo = _grafo_pesos_distintos()
    kruskal_fabricado = _fabrica_resultado(
        "kruskal", [("A", "B", 1), ("B", "C", 2), ("C", "D", 3)], 6.0, nodes="ABCD"
    )
    prim_fabricado = _fabrica_resultado(
        "prim", [("A", "B", 1), ("A", "C", 5)], 6.0, nodes="ABCD"
    )

    # Act
    comparacao = compare_results(grafo, kruskal_fabricado, prim_fabricado)

    # Assert
    assert comparacao["same_cost"] is True
    assert comparacao["same_edges"] is False
    assert comparacao["has_weight_ties"] is False
    assert comparacao["is_consistent"] is False
    assert "problema na implementação" in comparacao["message"]


def test_custos_diferentes_generam_mensagem_erro_grave_e_inconsistencia():
    # Arrange
    grafo = _grafo_pesos_distintos()
    kruskal_resultado = _fabrica_resultado(
        "kruskal", [("A", "B", 1), ("B", "C", 2), ("C", "D", 3)], 6.0, nodes="ABCD"
    )
    prim_resultado = _fabrica_resultado(
        "prim", [("A", "B", 1), ("B", "C", 2), ("C", "D", 3)], 9.0, nodes="ABCD"
    )

    # Act
    comparacao = compare_results(grafo, kruskal_resultado, prim_resultado)

    # Assert
    assert comparacao["same_cost"] is False
    assert comparacao["is_consistent"] is False
    assert comparacao["message"].startswith("ERRO GRAVE")


def test_cost_difference_é_absoluto_e_diferenca_pequena_é_mesmo_custo():
    # Arrange
    grafo = construir_grafo([no("A"), no("B")], [aresta("A", "B", 1.0)])
    base = _fabrica_resultado("kruskal", [("A", "B", 1.0)], 1.0, nodes="AB")

    # Act: diferença dentro da tolerância
    quase_igual = copy(base)
    quase_igual.total_cost = 1.0 + 5e-7
    comparacao = compare_results(grafo, base, quase_igual)

    # Assert
    assert comparacao["same_cost"] is True
    assert comparacao["cost_difference"] == pytest.approx(5e-7)
    assert 0.0 <= comparacao["cost_difference"] <= 1e-6

    # Act: diferença acima da tolerância
    diferente = copy(base)
    diferente.total_cost = 2.0
    comparacao = compare_results(grafo, base, diferente)

    # Assert
    assert comparacao["same_cost"] is False
    assert comparacao["cost_difference"] == 1.0
    assert comparacao["cost_difference"] > 1e-6


def test_arestas_exclusivas_em_empates_estao_corretas_em_ambos_lados(
    grafo_com_empates,
):
    # Arrange
    grafo = grafo_com_empates

    # Act
    resposta = run_algorithms(grafo, algorithm="both")
    comparacao = resposta["comparison"]

    # Assert: as exclusivas são exatamente a diferença simétrica dos conjuntos.
    assert comparacao["same_cost"] is True
    assert comparacao["kruskal_only_edges"] == []
    assert comparacao["prim_only_edges"] == []
    todos_k = _pares(resposta["kruskal"]["edges"])
    todos_p = _pares(resposta["prim"]["edges"])
    assert _pares(comparacao["kruskal_only_edges"]) == todos_k - todos_p
    assert _pares(comparacao["prim_only_edges"]) == todos_p - todos_k


def test_arestas_exclusivas_quando_algoritmos_divergem_em_empate():
    # Arrange: ciclo de 4 com todos os pesos 1; resultados fabricados
    # divergem deliberadamente para exercitar os lados exclusivos.
    grafo = construir_grafo(
        [no(v) for v in "ABCD"],
        [
            aresta("A", "B", 1),
            aresta("B", "C", 1),
            aresta("C", "D", 1),
            aresta("D", "A", 1),
        ],
    )
    kruskal_resultado = _fabrica_resultado(
        "kruskal", [("A", "B", 1), ("A", "D", 1), ("B", "C", 1)], 3.0, nodes="ABCD"
    )
    prim_resultado = _fabrica_resultado(
        "prim", [("A", "B", 1), ("B", "C", 1), ("C", "D", 1)], 3.0, nodes="ABCD"
    )

    # Act
    comparacao = compare_results(grafo, kruskal_resultado, prim_resultado)

    # Assert
    assert comparacao["has_weight_ties"] is True
    assert _pares(comparacao["kruskal_only_edges"]) == {("A", "D")}
    assert _pares(comparacao["prim_only_edges"]) == {("C", "D")}


def test_compare_results_com_apenas_um_resultado_tem_campos_nulos_e_mensagem_orientativa(
    grafo_classico,
):
    # Arrange
    apenas_kruskal = algoritmo_kruskal(grafo_classico)

    # Act
    comparacao = compare_results(grafo_classico, apenas_kruskal, None)

    # Assert
    for campo in COMPARACAO_CAMPOS_NULOS:
        assert comparacao[campo] is None
    assert comparacao["kruskal_only_edges"] == []
    assert comparacao["prim_only_edges"] == []
    assert (
        comparacao["message"]
        == "Execute os dois algoritmos para ver a comparação completa."
    )


def test_compare_results_com_nenhum_resultado_tem_campos_nulos_e_mensagem_orientativa(
    grafo_classico,
):
    # Arrange
    grafo = grafo_classico

    # Act
    comparacao = compare_results(grafo, None, None)

    # Assert
    for campo in COMPARACAO_CAMPOS_NULOS:
        assert comparacao[campo] is None
    assert comparacao["kruskal_only_edges"] == []
    assert comparacao["prim_only_edges"] == []
    assert (
        comparacao["message"]
        == "Execute os dois algoritmos para ver a comparação completa."
    )


def test_verify_false_devolve_verificacao_none(grafo_classico):
    # Arrange
    grafo = grafo_classico

    # Act
    resposta = run_algorithms(grafo, algorithm="both", verify=False)

    # Assert
    assert resposta["verification"] is None


def test_trace_true_devolve_resultados_com_trace_e_false_none(grafo_classico):
    # Arrange
    grafo = grafo_classico

    # Act
    com_trace = run_algorithms(grafo, algorithm="both", trace=True)
    sem_trace = run_algorithms(grafo, algorithm="both", trace=False)

    # Assert
    assert isinstance(com_trace["kruskal"]["trace"], list)
    assert len(com_trace["kruskal"]["trace"]) > 0
    assert isinstance(com_trace["prim"]["trace"], list)
    assert len(com_trace["prim"]["trace"]) > 0
    assert sem_trace["kruskal"]["trace"] is None
    assert sem_trace["prim"]["trace"] is None


def test_graph_stats_devolve_resumo_correto(grafo_desconexo):
    # Arrange: componentes {A, B}, {C, D} e {E}.
    grafo = grafo_desconexo

    # Act
    estatisticas = graph_stats(grafo)

    # Assert
    assert estatisticas["n_nodes"] == 5
    assert estatisticas["n_edges"] == 2
    assert estatisticas["n_components"] == 3
    assert estatisticas["is_connected"] is False
    assert estatisticas["n_divisa_edges"] == 0
    assert estatisticas["n_manual_edges"] == 0
    assert estatisticas["component_sizes"] == [2, 2, 1]


def test_graph_stats_vem_no_registro_de_execução(grafo_desconexo):
    # Arrange
    grafo = grafo_desconexo

    # Act
    resposta = run_algorithms(grafo, algorithm="both")

    # Assert
    estatisticas = resposta["graph_stats"]
    assert set(estatisticas) == ESTATISTAS_ESPERADOS
    assert estatisticas["n_components"] == 3
    assert estatisticas["is_connected"] is False


def test_graph_to_dict_devolve_nos_arestas_ordenados_descartados_warnings_e_stats():
    # Arrange
    grafo = construir_grafo_classico()
    avisos = ["aviso de exemplo"]
    descartados = [{"id": "X", "name": "Descartado", "reason": "exemplo"}]

    # Act
    dicionario = graph_to_dict(grafo, warnings=avisos, discarded=descartados)

    # Assert
    ids = [no["id"] for no in dicionario["nodes"]]
    assert ids == sorted(ids)
    assert ids == [node.id for node in sorted(grafo.nodes.values(), key=lambda n: n.id)]
    pares_ordenados = sorted(
        (min(e["u"], e["v"]), max(e["u"], e["v"])) for e in dicionario["edges"]
    )
    pares_saida = [
        (min(e["u"], e["v"]), max(e["u"], e["v"])) for e in dicionario["edges"]
    ]
    assert pares_saida == pares_ordenados
    assert dicionario["warnings"] == avisos
    assert dicionario["discarded"] == descartados
    assert set(dicionario["stats"]) == ESTATISTAS_ESPERADOS


def test_avisos_do_grafo_sao_propagados_para_resposta_de_execução(
    grafo_desconexo,
):
    # Arrange
    grafo = grafo_desconexo

    # Act
    resposta = run_algorithms(grafo, algorithm="both")

    # Assert
    assert resposta["warnings"] == list(grafo.warnings)
    assert any("desconexo" in aviso for aviso in resposta["warnings"])


# ---------------------------------------------------------------------------
# B-01..B-10: benchmark
# ---------------------------------------------------------------------------


def test_run_benchmark_p3_com_uma_execucao_tem_sete_linhas_e_ultima_644_por_1832():
    # Arrange
    runs = 1

    # Act
    payload = run_benchmark(runs=runs)

    # Assert
    linhas = payload["rows"]
    assert len(linhas) == 8
    nos = [linha["n_nodes"] for linha in linhas]
    arestas = [linha["n_edges"] for linha in linhas]
    assert arestas == sorted(arestas)
    assert linhas[-1]["n_nodes"] == 644
    assert linhas[-1]["n_edges"] == 1832


def test_estrutura_das_medicoes_tem_tempos_finitos_e_percentis_ordenados():
    # Arrange
    payload = run_benchmark(runs=1)

    # Act + Assert
    for linha in payload["rows"]:
        for campo in (
            "kruskal_ms",
            "kruskal_p25_ms",
            "kruskal_p75_ms",
            "prim_ms",
            "prim_p25_ms",
            "prim_p75_ms",
        ):
            valor = linha[campo]
            assert math.isfinite(valor)
            assert valor >= 0
        assert linha["kruskal_p25_ms"] <= linha["kruskal_ms"] <= linha["kruskal_p75_ms"]
        assert linha["prim_p25_ms"] <= linha["prim_ms"] <= linha["prim_p75_ms"]


def test_benchmark_informa_metadados_corretos():
    # Arrange
    runs = 3

    # Act
    meta = run_benchmark(runs=runs)["meta"]

    # Assert
    assert meta["preset_id"] == "p3-estado-sp"
    assert "São Paulo" in meta["preset_name"]
    assert meta["start_city"] == "3506003"
    assert meta["start_city_name"] == "Bauru"
    assert meta["runs"] == runs
    assert "milissegundos" in meta["note"]


def test_benchmark_limita_runs_ao_intervalo_1_a_100():
    # Act + Assert
    assert run_benchmark(runs=0)["meta"]["runs"] == 1
    assert run_benchmark(runs=-10)["meta"]["runs"] == 1
    assert run_benchmark(runs=200)["meta"]["runs"] == 100
    assert run_benchmark(runs=100)["meta"]["runs"] == 100
    # (A validação HTTP 422 pela API é de escopo da camada de rotas; aqui testa-se o serviço.)


def test_preset_inexistente_gera_not_found_error():
    # Act + Assert
    with pytest.raises(NotFoundError):
        run_benchmark(preset_id="p9-nao-existe", runs=1)


def test_cidade_inicial_inexistente_gera_not_found_error():
    # Act + Assert
    with pytest.raises(NotFoundError):
        run_benchmark(start_city_name="Município Que Não Existe", runs=1)


def test_cidade_inicial_fora_do_preset_gera_not_found_error():
    # Arrange: Presidente Prudente existe no estado, mas não está no preset p1
    # (Bauru e vizinhos diretos).
    # Act + Assert
    with pytest.raises(NotFoundError):
        run_benchmark(
            preset_id="p1-bauru-vizinhos",
            start_city_name="Presidente Prudente",
            runs=1,
        )


def test_benchmark_repetido_mantem_estrutura_identica_sem_comparar_tempos_absolutos():
    # Arrange
    primeira = run_benchmark(runs=1)
    segunda = run_benchmark(runs=1)

    # Act + Assert: estrutura idêntica; tempos não são comparados.
    assert [linha["n_nodes"] for linha in primeira["rows"]] == [
        linha["n_nodes"] for linha in segunda["rows"]
    ]
    assert [linha["n_edges"] for linha in primeira["rows"]] == [
        linha["n_edges"] for linha in segunda["rows"]
    ]
    assert [list(linha.keys()) for linha in primeira["rows"]] == [
        list(linha.keys()) for linha in segunda["rows"]
    ]
    for chave in ("preset_id", "preset_name", "start_city", "start_city_name", "runs"):
        assert primeira["meta"][chave] == segunda["meta"][chave]


def test_benchmark_preset_pequeno_nao_quebra_mesmo_com_tamanhos_repetidos():
    # Arrange: BUG-016 — setdefault(len(ball), ...) pode descartar
    # subgrafos de tamanho igual nos presets pequenos p1/p2.
    # Act + Assert: não deve quebrar e deve devolver linhas com estrutura válida.
    for preset_id in ("p1-bauru-vizinhos", "p2-regiao-bauru"):
        payload = run_benchmark(preset_id=preset_id, runs=1)
        assert len(payload["rows"]) >= 1
        for linha in payload["rows"]:
            assert isinstance(linha["n_nodes"], int) and linha["n_nodes"] > 0
            assert isinstance(linha["n_edges"], int) and linha["n_edges"] >= 0


def test_benchmark_atual_usa_apenas_subgrafos_do_p3_sem_instancia_densa(monkeypatch):
    # Arrange: B-09 (CONF) — o PLAN §7.5 prevê comparação esparso × denso. Após
    # BUG-035, o benchmark inclui uma instância densa determinística em meta.
    assinatura = signature(run_benchmark)
    assert assinatura.parameters["preset_id"].default == "p3-estado-sp"

    carregados = []
    original_get_preset = modulo_benchmark.get_preset

    def espião(preset_id):
        carregados.append(preset_id)
        return original_get_preset(preset_id)

    monkeypatch.setattr(modulo_benchmark, "get_preset", espião)

    # Act
    payload = run_benchmark(runs=1)

    # Assert: o benchmark carrega p3-estado-sp e agora inclui instância densa.
    assert carregados == ["p3-estado-sp"]
    assert "dense_instance" in payload["meta"]
    denso = payload["meta"]["dense_instance"]
    assert denso["n_nodes"] == 60
    assert denso["seed"] == 20260335
    assert denso["n_edges"] > 0


def test_measure_mede_execucoes_sem_trace(monkeypatch):
    # Arrange: B-10 — _measure deve chamar os algoritmos sem trace.
    grafo = construir_grafo([no("A")], [])
    chamadas_trace = []

    def falso_algoritmo(grafo, trace=False):
        chamadas_trace.append(trace)
        return MSTResult(
            algorithm="falso",
            edges=[],
            total_cost=0.0,
            n_components=1,
            components=[["A"]],
            is_forest=True,
            metrics={"time_ms": 7.5},
        )

    monkeypatch.setattr(modulo_benchmark, "kruskal", falso_algoritmo)

    # Act
    resumo = _measure(grafo, "kruskal", runs=3)

    # Assert: aquecimento + 3 execuções, todas sem trace, e o tempo medido vem
    # da execução limpa (sem trace).
    assert chamadas_trace == [False, False, False, False]
    assert resumo["median"] == 7.5
    assert resumo["min"] == 7.5
    assert resumo["max"] == 7.5
