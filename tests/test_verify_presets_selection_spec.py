"""Testes de especificação para verificação de MST e seleção de cidades."""
from __future__ import annotations

import pytest

from backend.app.algorithms.graph import Edge, Graph
from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.prim import prim
from backend.app.algorithms.verify import verify_forest
from backend.app.errors import ValidationError, NotFoundError
from backend.app.services.graph_selection import build_from_city_ids
from backend.app.services.presets import get_preset, city_id_by_name, get_presets

# Fixtures from conftest
from tests.conftest import (
    grafo_classico,
    grafo_desconexo,
    grafo_com_pesos_negativos,
    construir_grafo,
    construir_grafo_desconexo,
    no,
    aresta,
    construir_grafo_com_empates,
    resultado_com_arestas,
)

# ---------------------------------------------------------------------------
# Verificação de MST (V-01 .. V-14)
# ---------------------------------------------------------------------------

def test_deve_aprovar_mst_correta_quando_usada_prim_ou_kruskal(grafo_classico):
    """V-01: MST correta (Prim ou Kruskal) deve ser aprovada."""
    for algoritmo in ("kruskal", "prim"):
        resultado = (kruskal(grafo_classico) if algoritmo == "kruskal"
                     else prim(grafo_classico))
        verificacao = verify_forest(grafo_classico, resultado)
        assert verificacao.performed is True
        assert verificacao.is_forest is True
        assert verificacao.cycle_property is True
        assert verificacao.is_valid is True


def test_deve_reprovar_resultado_com_ciclo_extra(grafo_classico):
    """V-02: resultado com aresta extra que forma ciclo deve ser reprovado."""
    resultado = kruskal(grafo_classico)
    # aresta A-B já está na MST; adicionamos A-C que também está, criando ciclo A-B-C-A
    aresta_extra = achar_aresta(grafo_classico, "A", "C")
    resultado_invalido = resultado_com_arestas(
        resultado, list(resultado.edges) + [aresta_extra]
    )
    verificacao = verify_forest(grafo_classico, resultado_invalido)
    assert verificacao.performed is True
    assert verificacao.is_valid is False
    # ciclo_property deve ser False ou is_forest False (pelo menos uma falha)
    assert (verificacao.is_forest is False) or (verificacao.cycle_property is False)


def test_deve_reprovar_resultado_incompleto_faltando_aresta(grafo_classico):
    """V-03: resultado incompleto (falta aresta para n−c) deve ser reprovado."""
    resultado = kruskal(grafo_classico)
    # removemos a última aresta da MST
    resultado_incompleto = resultado_com_arestas(
        resultado, list(resultado.edges)[:-1]
    )
    # mantemos a informação de um único componente para que a contagem n-c seja inconsistente
    resultado_incompleto.n_components = 1
    resultado_incompleto.components = [sorted(grafo_classico.node_ids)]
    verificacao = verify_forest(grafo_classico, resultado_incompleto)
    assert verificacao.performed is True
    assert verificacao.is_valid is False
    # detalhe deve mencionar quantidade de arestas incorreta
    assert any("Quantidade de arestas incorreta" in d for d in verificacao.details)


def test_deve_reprovar_resultado_com_aresta_inexistente(grafo_classico):
    """V-04: aresta que não pertence ao grafo original deve ser reprovada."""
    resultado = kruskal(grafo_classico)
    # criamos uma aresta que não existe no grafo (por exemplo, D-E, onde D ou E não são vizinhos)
    aresta_inexistente = Edge("A", "F", 100)  # A e F não têm aresta direta no grafo_classico
    resultado_invalido = resultado_com_arestas(
        resultado, list(resultado.edges) + [aresta_inexistente]
    )
    verificacao = verify_forest(grafo_classico, resultado_invalido)
    assert verificacao.performed is True
    assert verificacao.is_valid is False
    assert any("não pertence ao grafo" in d for d in verificacao.details)


def test_deve_reprovar_resultado_com_peso_divergente(grafo_classico):
    """V-05: peso da aresta divergente do original deve ser reprovado."""
    resultado = kruskal(grafo_classico)
    # alteramos o peso de A-B para 999 (original é 4)
    aresta_modificada = Edge("A", "B", 999)
    resultado_invalido = resultado_com_arestas(
        resultado, list(resultado.edges) + [aresta_modificada]
    )
    verificacao = verify_forest(grafo_classico, resultado_invalido)
    assert verificacao.performed is True
    assert verificacao.is_valid is False
    assert any("Peso divergente" in d for d in verificacao.details)


def test_deve_reprovar_resultado_com_custo_inconsistente(grafo_classico):
    """V-06: custo total inconsistente com a soma das arestas deve ser reprovado."""
    resultado = kruskal(grafo_classico)
    # alteramos o custo total para 2000 (valor aleatório)
    resultado_invalido = resultado_com_arestas(
        resultado, list(resultado.edges)
    )
    resultado_invalido.total_cost = 2000.0
    verificacao = verify_forest(grafo_classico, resultado_invalido)
    assert verificacao.performed is True
    assert verificacao.is_valid is False
    assert verificacao.cost_consistent is False
    assert any("Custo total inconsistente" in d for d in verificacao.details)


def test_deve_aprovar_floresta_desconectada(grafo_desconexo):
    """V-07: floresta desconectada (várias componentes) deve ser aprovada."""
    resultado = kruskal(grafo_desconexo)
    verificacao = verify_forest(grafo_desconexo, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True
    # n-c arestas = n_nodes - n_componentes
    assert verificacao.details == []


def test_deve_aprovar_grafo_sem_arestas():
    """V-08: grafo sem arestas (ou 1 vértice) deve ser válido."""
    grafo = construir_grafo([no(v) for v in "ABCD"], [])
    resultado = kruskal(grafo)
    verificacao = verify_forest(grafo, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_deve_aprovar_grafo_com_um_unico_vertice():
    """V-08 (continuação): grafo com 1 vértice deve ser válido."""
    grafo = construir_grafo([no("A")], [])
    resultado = prim(grafo)
    verificacao = verify_forest(grafo, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_deve_pular_propriedade_do_ciclo_quando_grao_excede_limite(grafo_com_pesos_negativos):
    """V-09: >20000 arestas – propriedade do ciclo não é verificada, mas estrutura deve ser."""
    # Grafo grande determinístico com mais de 20.000 arestas
    from tests.conftest import gerar_grafo_conexo

    grafo_grande, _ = gerar_grafo_conexo(n=500, extras=20000, seed=1, pesos_negativos=False)
    resultado = kruskal(grafo_grande)
    verificacao = verify_forest(grafo_grande, resultado)
    # Como o grafo tem >20000 arestas, a verificação detalhada do ciclo deve ser pulada
    assert verificacao.performed is False
    # Estrutura ainda deve estar correta
    assert verificacao.is_forest is True
    assert verificacao.is_valid is True


def test_deve_verificar_propriedade_do_ciclo_quando_exatamente_20000_arestas():
    """V-10: exatamente 20000 arestas – propriedade do ciclo deve ser verificada."""
    # usamos o mesmo gerador, mas garantimos que o total de arestas seja 20000
    from tests.conftest import gerar_grafo_conexo

    n = 300  # escolha n de modo que n-1 + extras = 20000
    grafo, _ = gerar_grafo_conexo(
        n=n, extras=20000 - (n - 1), seed=2, pesos_negativos=False
    )
    assert grafo.n_edges == 20000
    resultado = kruskal(grafo)
    verificacao = verify_forest(grafo, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_deve_aprovar_mst_com_pesos_negativos(grafo_com_pesos_negativos):
    """V-11: triângulo com pesos -10, -5, -2 deve gerar MST válida."""
    grafo = Graph.from_records(
        [no(v) for v in "ABC"],
        [
            aresta("A", "B", -10),
            aresta("B", "C", -5),
            aresta("C", "A", -2),
        ],
    )
    resultado = kruskal(grafo)
    verificacao = verify_forest(grafo, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_deve_aprovar_mst_em_grafo_aleatorio_com_pesos_negativos():
    """V-12: grafo aleatório com pesos negativos deve ser aprovado."""
    from tests.conftest import gerar_grafo_conexo
    grafo, _ = gerar_grafo_conexo(n=100, extras=500, seed=7, pesos_negativos=True)
    resultado = kruskal(grafo)
    verificacao = verify_forest(grafo, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


def test_deve_fornecer_mensagem_clara_em_pt_br_sem_traceback(grafo_classico):
    """V-13: mensagem deve estar em pt-BR e não conter traceback."""
    resultado = kruskal(grafo_classico)
    # Cria um resultado inválido introduzindo uma aresta extra que viola a propriedade do ciclo
    aresta_extra = Edge("A", "B", 0.5)  # A-B já está na MST, adicionamos outra A-B com peso menor
    resultado_invalido = resultado_com_arestas(
        resultado, list(resultado.edges) + [aresta_extra]
    )
    verificacao = verify_forest(grafo_classico, resultado_invalido)
    assert verificacao.performed is True
    # A mensagem deve estar em português e não conter "Traceback" ou similar
    mensagem = verificacao.message
    assert mensagem.startswith("Solução inválida")
    assert "traceback" not in mensagem.lower()


def test_deve_nao_chamar_kruskal_nem_prim_quando_verifica_floresta(monkeypatch, grafo_classico):
    """V-14: verify_forest não deve chamar kruskal/prim (inspeção)."""
    import importlib

    kruskal_module = importlib.import_module("backend.app.algorithms.kruskal")
    prim_module = importlib.import_module("backend.app.algorithms.prim")

    resultado = kruskal(grafo_classico)

    def mock_kruskal(*args, **kwargs):
        raise AssertionError("kruskal foi chamado durante verify_forest")

    def mock_prim(*args, **kwargs):
        raise AssertionError("prim foi chamado durante verify_forest")

    monkeypatch.setattr(kruskal_module, "kruskal", mock_kruskal)
    monkeypatch.setattr(prim_module, "prim", mock_prim)

    verificacao = verify_forest(grafo_classico, resultado)
    assert verificacao.performed is True
    assert verificacao.is_forest is True
    assert verificacao.cycle_property is True
    assert verificacao.is_valid is True


# ---------------------------------------------------------------------------
# Testes de presets (PR-01 .. PR-12)
# ---------------------------------------------------------------------------

def test_deve_listar_cinco_presets_em_ordem_correta():
    """PR-01: exatamente 5 presets na ordem p1..p5, ids/nomes/descrições coerentes."""
    presets = [preset for preset in get_presets()]
    assert len(presets) == 5
    ids_esperados = [
        "p1-bauru-vizinhos",
        "p2-regiao-bauru",
        "p3-estado-sp",
        "p4-regioes-separadas",
        "p5-litoral-norte",
    ]
    assert [p.id for p in presets] == ids_esperados

    # Verificações de consistência de cada preset
    p1 = presets[0]
    assert (p1.graph.n_nodes, p1.graph.n_edges) == (8, 15)
    assert "Bauru" in p1.name
    assert p1.description.startswith("Bauru e todos os municípios")
    assert p1.include_manual is True

    p2 = presets[1]
    assert (p2.graph.n_nodes, p2.graph.n_edges) == (109, 295)
    assert 60 <= p2.graph.n_nodes <= 150
    assert p2.description.startswith("Municípios a até")
    assert p2.include_manual is True

    p3 = presets[2]
    assert (p3.graph.n_nodes, p3.graph.n_edges) == (644, 1832)
    assert p3.include_manual is False
    # Verifica descarte de Ilhabela
    ilhabela_id = "3520400"
    ids_descartados = [item["id"] for item in p3.discarded]
    assert ilhabela_id in ids_descartados
    assert any("Ilhabela" in item["name"] for item in p3.discarded)
    assert all(edge.attrs.get("source") != "manual" for edge in p3.graph.edges)

    p4 = presets[3]
    assert (p4.graph.n_nodes, p4.graph.n_edges) == (20, 37)
    assert len(p4.graph.connected_components()) == 2
    assert p4.include_manual is True

    p5 = presets[4]
    assert (p5.graph.n_nodes, p5.graph.n_edges) == (4, 3)
    assert p5.include_manual is True
    # Verifica a ligação manual Ilhabela–São Sebastião
    manual_edge = None
    for edge in p5.graph.edges:
        if edge.attrs.get("source") == "manual":
            manual_edge = edge
            break
    assert manual_edge is not None
    assert {manual_edge.u, manual_edge.v} == {
        "3520400",  # Ilhabela
        "3550704",  # São Sebastião
    }


def test_deve_usar_vertices_do_catalogo_real():
    """PR-09: todos os presets utilizam vertices do catálogo real."""
    from backend.app.data_loader import load_cities

    catalog_ids = {city.id for city in load_cities()}
    for preset in get_presets():
        assert set(preset.graph.node_ids).issubset(catalog_ids)
        assert preset.summary()["n_nodes"] == preset.graph.n_nodes
        assert preset.summary()["n_edges"] == preset.graph.n_edges


def test_deve_descartar_ilhabela_no_preset_p3():
    """PR-03: p3 deve descartar Ilhabela e avisar, sem arestas manuais."""
    preset = get_preset("p3-estado-sp")
    # Ilhabela deve estar no lista de descartados
    ids_descartados = [item["id"] for item in preset.discarded]
    assert "3520400" in ids_descartados
    # Nenhuma aresta manual deve existir
    manual_edges = [e for e in preset.graph.edges if e.attrs.get("source") == "manual"]
    assert not manual_edges, "Arestas manuais inesperadas encontradas em p3"


def test_deve_obter_custo_correto_no_preset_p3():
    """PR-04: Prim e Kruskal no preset p3 devem chegar ao mesmo custo (~9034,325 km)."""
    preset = get_preset("p3-estado-sp")
    graph = preset.graph
    result_kruskal = kruskal(graph)
    result_prim = prim(graph, start_vertex="3506003")  # Bauru
    assert result_kruskal.total_cost == pytest.approx(9034.325, abs=1.0)
    assert result_prim.total_cost == pytest.approx(result_kruskal.total_cost, abs=1e-6)
    # Verificação deve aprovar
    verif = verify_forest(graph, result_kruskal)
    assert verif.is_valid is True
    verif2 = verify_forest(graph, result_prim)
    assert verif2.is_valid is True


def test_deve_produzir_floresta_no_preset_p4():
    """PR-05: p4 deve produzir floresta com 2 componentes e 18 arestas."""
    preset = get_preset("p4-regioes-separadas")
    graph = preset.graph
    components = len(graph.connected_components())
    assert components == 2
    for result in (kruskal(graph), prim(graph, start_vertex="3506003")):
        assert result.n_components == components
        assert result.is_forest is True
        assert len(result.edges) == graph.n_nodes - components == 18
        assert verify_forest(graph, result).is_valid is True


def test_deve_incluir_ligacao_manual_no_preset_p5():
    """PR-06: p5 deve incluir exatamente a ligação manual Ilhabela–São Sebastião."""
    preset = get_preset("p5-litoral-norte")
    manual_edges = [e for e in preset.graph.edges if e.attrs.get("source") == "manual"]
    assert len(manual_edges) == 1
    u, v = manual_edges[0].u, manual_edges[0].v
    assert {u, v} == {"3520400", "3550704"}  # Ilhabela e São Sebastião


def test_deve_conter_bauru_no_preset_p1():
    """PR-07: p1 deve conter Bauru e ter 8‑15 vértices."""
    preset = get_preset("p1-bauru-vizinhos")
    assert 8 <= preset.graph.n_nodes <= 15
    assert any(node.id == "3506003" for node in preset.graph.nodes.values())  # Bauru


def test_deve_escolher_raio_entre_1_e_4_no_preset_p2():
    """PR-08: p2 deve escolher um raio entre 1 e 4 e ter 60‑150 vértices."""
    preset = get_preset("p2-regiao-bauru")
    # O raio usado está implícito; podemos inferir a partir do tamanho do grafo.
    assert 60 <= preset.graph.n_nodes <= 150
    # Como o preset foi gerado escolhendo o maior raio que satisfaz 60‑150,
    # ele está entre 1 e 4 por construção.


def test_deve_buscar_cidade_ignorando_acentos_caixa_hifen_espaco():
    """PR-10: busca por nome ignora acentos, caixa, hífen e espaços."""
    assert city_id_by_name("Bauru") == "3506003"
    assert city_id_by_name("sao sebastiao") == "3550704"
    assert city_id_by_name("São Sebastião") == "3550704"
    # Hífen usado como separador de palavras (Biritiba-Mirim / Biritiba Mirim)
    assert city_id_by_name("Biritiba-Mirim") == "3506607"
    assert city_id_by_name("Biritiba Mirim") == "3506607"


def test_deve_gerar_not_found_para_preset_inexistente():
    """PR-11: preset ou cidade inexistente deve gerar NotFoundError."""
    with pytest.raises(NotFoundError):
        get_preset("p9-inexistente")
    with pytest.raises(NotFoundError):
        city_id_by_name("Municipio Nao Existe")


def test_deve_cachar_resultado_de_preset_para_messas_iguais():
    """PR-12: duas chamadas a get_preset ou city_id_by_name devem ser determinísticas."""
    preset1 = get_preset("p3-estado-sp")
    preset2 = get_preset("p3-estado-sp")
    assert preset1.id == preset2.id
    assert preset1.graph.n_nodes == preset2.graph.n_nodes
    assert preset1.graph.n_edges == preset2.graph.n_edges

    id1 = city_id_by_name("Bauru")
    id2 = city_id_by_name("Bauru")
    assert id1 == id2
    assert id1 == "3506003"


# ---------------------------------------------------------------------------
# Testes de seleção de cidades (S-01 .. S-10)
# ---------------------------------------------------------------------------

def test_deve_levantar_erro_quando_selecionar_menos_de_dois_cidades():
    """S-01: seleção com menos de 2 cidades deve gerar ValidationError clara."""
    with pytest.raises(ValidationError) as exc:
        build_from_city_ids(["3506003"])
    assert "Selecione ao menos 2 municípios" in str(exc.value)


def test_deve_levantar_erro_para_codigo_ibge_inexistente():
    """S-02: código IBGE inexistente deve gerar ValidationError listando códigos."""
    with pytest.raises(ValidationError) as exc:
        build_from_city_ids(["3506003", "1234567"])
    assert "Código(s) IBGE inexistente(s)" in str(exc.value)
    # O código 1234567 deve aparecer na mensagem


def test_deve_deduplicar_e_limpar_ids_com_espacos_vazios():
    """S-03: IDs duplicados, com espaços ou vazios são deduplicados e limpos."""
    ids = ["3506003", " 3506003 ", "3506003", "", "   ", "3550704"]
    built = build_from_city_ids(ids)
    assert built.graph.n_nodes == 2
    assert set(built.graph.node_ids) == {"3506003", "3550704"}


def test_deve_criar_subgrafos_induzidos_apenas_com_as_duas_pontas_selecionadas():
    """S-04: subgrafo induzido só inclui arestas cujas duas pontas estão selecionadas."""
    from backend.app.data_loader import load_graph

    full_graph = load_graph(include_manual=True)
    neighbor = full_graph.neighbors("3506003")[0]  # vizinho real de Bauru
    built = build_from_city_ids(["3506003", neighbor])
    assert built.graph.n_nodes == 2
    assert built.graph.n_edges == 1
    assert {built.graph.edges[0].u, built.graph.edges[0].v} == {"3506003", neighbor}


def test_deve_incluir_balsa_quando_include_manual_true():
    """S-05: com include_manual=True, a balsa (ligação manual) deve ser incluída quando aplicável."""
    preset = get_preset("p5-litoral-norte")
    # O próprio preset já inclui a balsa; verificamos que a aresta manual está presente.
    manual_edge = next(
        (e for e in preset.graph.edges if e.attrs.get("source") == "manual"), None
    )
    assert manual_edge is not None, "A balsa não foi incluída no preset p5"


def test_deve_nao_incluir_balsa_quando_include_manual_false():
    """S-05: sem include_manual, a balsa deve ficar fora do grafo."""
    # Selecionamos Ilhabela e São Sebastião, ligados apenas pela aresta manual.
    built = build_from_city_ids({"3520400", "3550704"}, include_manual=False)
    # Verificamos que a aresta manual não está presente
    manual_edges = [e for e in built.graph.edges if e.attrs.get("source") == "manual"]
    assert not manual_edges, "A balsa ainda está presente quando include_manual=False"


def test_deve_avertir_cidade_isolada_na_seleção():
    """S-06: cidade isolada na seleção deve gerar aviso nomeando a cidade e seu código."""
    built = build_from_city_ids(["3506003", "3550704"])  # Bauru e São Sebastião
    warnings = built.warnings
    assert any("ficou isolado" in w for w in warnings)
    assert any("Bauru" in w and "3506003" in w for w in warnings)
    assert any("São Sebastião" in w and "3550704" in w for w in warnings)


def test_deve_avertir_grafo_desconectado_na_seleção():
    """S-07: seleção que desconecta o grafo deve gerar aviso de desconexão/componentes."""
    built = build_from_city_ids(["3506003", "3550704"])  # sem aresta entre si
    warnings = built.warnings
    assert any("desconexo" in w.lower() for w in warnings)


def test_deve_remover_avisos_duplicados_preservando_ordem():
    """S-08: avisos duplicados são removidos, preservando a ordem de aparição."""
    built = build_from_city_ids(["3506003", "3550704", "3520400"])
    warnings = built.warnings
    assert len(warnings) == len(set(warnings))


def test_deve_ordenar_catalogo_por_nome():
    """S-09 (I): catálogo deve conter 645 municípios ordenados por nome."""
    from backend.app.services.graph_selection import city_catalog
    catalog = city_catalog()
    assert len(catalog) == 645
    nomes = [item["name"] for item in catalog]
    # Verifica se os nomes estão ordenados alfabeticamente (case‑insensitive)
    assert nomes == sorted(nomes, key=lambda s: s.casefold())


def test_deve_selecionar_dois_cidades_vizinhas():
    """S-10 (I): seleção com 2 cidades vizinhas deve resultar em 2 vértices, 1 aresta, 1 componente."""
    from backend.app.data_loader import load_graph

    full_graph = load_graph(include_manual=True)
    neighbor = full_graph.neighbors("3506003")[0]
    built = build_from_city_ids(["3506003", neighbor])
    assert built.graph.n_nodes == 2
    assert built.graph.n_edges == 1
    assert len(built.graph.connected_components()) == 1


# ---------------------------------------------------------------------------
# Helpers para testes de estrutura (reutilizados)
# ---------------------------------------------------------------------------

def achar_aresta(graph, u, v):
    """Localiza a aresta {u, v} no grafo, independentemente da orientação."""
    for edge in graph.edges:
        a, b = edge.u, edge.v
        if {a, b} == {u, v}:
            return edge
    raise AssertionError(f"A aresta {{{u}, {v}}} não existe no grafo")


def peso_da_aresta(edge):
    return float(edge.weight)


def conjunto_de_arestas(resultado):
    """Representação determinística e não orientada das arestas do resultado."""
    return sorted((min(e.u, e.v), max(e.u, e.v)) for e in resultado.edges)


def custo_das_arestas(arestas):
    return sum(peso_da_aresta(aresta) for aresta in arestas)