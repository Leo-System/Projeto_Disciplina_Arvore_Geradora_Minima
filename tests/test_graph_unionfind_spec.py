"""Testes de especificação do domínio Graph (G-01..G-24) e Union-Find (U-01..U-08).

Padrão AAA (Arrange-Act-Assert) e nomes em português "deve ... quando ...".
Apenas o comportamento esperado pelo PLAN é testado; nenhum skip/xfail/only.
"""

from __future__ import annotations

import json
import random

import pytest

from backend.app.algorithms.graph import Edge, Graph, GraphValidationError, Node
from backend.app.algorithms.union_find import UnionFind
from conftest import (
    achar_aresta,
    aresta,
    construir_grafo,
    construir_grafo_classico,
    construir_grafo_com_pesos_negativos,
    construir_grafo_desconexo,
    conjunto_de_arestas,
    extremidades,
    no,
    peso_da_aresta,
)


# ---------------------------------------------------------------------------
# G-01 .. G-06
# ---------------------------------------------------------------------------

def test_deve_expor_atributos_da_construcao_basica():
    grafo = construir_grafo_classico()

    assert grafo.n_nodes == 6
    assert grafo.n_edges == 9
    assert grafo.node_ids == sorted("ABCDEF")
    assert set(grafo.nodes) == set("ABCDEF")
    assert len(grafo.edges) == grafo.n_edges
    assert set(grafo.adjacency) == set("ABCDEF")
    total_incidentes = sum(len(incidentes) for incidentes in grafo.adjacency.values())
    assert total_incidentes == 2 * grafo.n_edges
    assert isinstance(grafo.warnings, list)
    assert all(isinstance(aviso, str) for aviso in grafo.warnings)


def test_deve_gerar_erro_quando_grafo_tem_zero_vertices():
    with pytest.raises(GraphValidationError):
        Graph.from_records([], [])


@pytest.mark.parametrize(
    "nodes",
    [
        [no("")],
        [no("A"), no("A")],
    ],
    ids=["id-vazio", "id-duplicado"],
)
def test_deve_gerar_erro_quando_vertice_tem_id_vazio_ou_duplicado(nodes):
    with pytest.raises(GraphValidationError):
        Graph.from_records(nodes, [])


@pytest.mark.parametrize(
    "aresta_invalida",
    [aresta("A", "Z", 1), aresta("Z", "B", 1)],
    ids=["destino-inexistente", "origem-inexistente"],
)
def test_deve_gerar_erro_citando_vertice_quando_aresta_referencia_vertice_inexistente(
    aresta_invalida,
):
    nodes = [no("A"), no("B")]
    with pytest.raises(GraphValidationError) as excinfo:
        Graph.from_records(nodes, [aresta_invalida])
    assert "Z" in str(excinfo.value)


@pytest.mark.parametrize(
    "peso_invalido",
    [
        "abc",
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        False,
    ],
    ids=[
        "texto",
        "none",
        "nan",
        "mais-infinito",
        "menos-infinito",
        "bool-verdadeiro",
        "bool-falso",
    ],
)
def test_deve_gerar_erro_para_cada_peso_invalido(peso_invalido):
    nodes = [no("A"), no("B")]
    with pytest.raises(GraphValidationError):
        Graph.from_records(nodes, [aresta("A", "B", peso_invalido)])


def test_deve_ignorar_laco_registrar_aviso_e_nao_lancar_erro():
    grafo = construir_grafo(
        [no("A"), no("B")],
        [aresta("A", "A", 5), aresta("A", "B", 2)],
    )

    assert grafo.n_nodes == 2
    assert grafo.n_edges == 1
    assert peso_da_aresta(grafo.edges[0]) == pytest.approx(2.0)
    assert grafo.warnings
    assert any("Laço ignorado em A." in aviso for aviso in grafo.warnings)


def test_deve_manter_um_vertice_sem_arestas_quando_grafo_contem_somente_um_laco():
    grafo = construir_grafo([no("A")], [aresta("A", "A", 1)])

    assert grafo.n_nodes == 1
    assert grafo.n_edges == 0
    assert grafo.node_ids == ["A"]
    assert grafo.warnings


# ---------------------------------------------------------------------------
# G-07 .. G-13
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pesos",
    [(5, 2), (2, 5)],
    ids=["maior-primeiro", "menor-primeiro"],
)
def test_deve_manter_aresta_de_menor_peso_e_uma_unica_aresta_quando_ha_duplicata_em_qualquer_ordem(
    pesos,
):
    grafo = construir_grafo(
        [no("A"), no("B")],
        [aresta("A", "B", pesos[0]), aresta("B", "A", pesos[1])],
    )

    assert grafo.n_edges == 1
    assert peso_da_aresta(grafo.edges[0]) == pytest.approx(min(pesos))
    assert grafo.warnings
    assert any(
        "Aresta duplicada A-B" in aviso and str(min(pesos)) in aviso
        for aviso in grafo.warnings
    )


def test_deve_aceitar_peso_negativo_com_aviso():
    grafo = construir_grafo([no("A"), no("B")], [aresta("A", "B", -7)])

    assert grafo.n_nodes == 2
    assert grafo.n_edges == 1
    assert peso_da_aresta(grafo.edges[0]) == pytest.approx(-7.0)
    assert any("peso negativo" in aviso.lower() for aviso in grafo.warnings)


def test_deve_aceitar_peso_zero():
    grafo = construir_grafo(
        [no("A"), no("B"), no("C")],
        [aresta("A", "B", 0), aresta("B", "C", 3)],
    )

    assert grafo.n_edges == 2
    assert peso_da_aresta(achar_aresta(grafo, "A", "B")) == pytest.approx(0.0)


def test_deve_ser_valido_quando_grafo_tem_um_vertice():
    grafo = construir_grafo([no("A")], [])

    assert grafo.n_nodes == 1
    assert grafo.n_edges == 0
    assert grafo.node_ids == ["A"]
    assert grafo.connected_components() == [["A"]]
    assert any("único vértice" in aviso for aviso in grafo.warnings)


def test_deve_ser_valido_e_avisar_vertices_isolados_quando_tem_mais_de_um_vertice_e_zero_arestas():
    grafo = construir_grafo([no(v) for v in "ABC"], [])

    assert grafo.n_nodes == 3
    assert grafo.n_edges == 0
    assert grafo.connected_components() == [["A"], ["B"], ["C"]]
    assert any("isolados" in aviso for aviso in grafo.warnings)


def test_deve_ser_valido_e_avisar_componentes_e_tamanhos_quando_grafo_eh_desconexo():
    grafo = construir_grafo_desconexo()

    componentes = grafo.connected_components()
    assert len(componentes) == 3
    assert any("desconexo" in aviso and "3 componentes" in aviso for aviso in grafo.warnings)
    assert any("tamanhos: 2, 2, 1" in aviso for aviso in grafo.warnings)


# ---------------------------------------------------------------------------
# G-14 .. G-17
# ---------------------------------------------------------------------------

def test_deve_normalizar_aresta_ordenar_par_reverter_e_serializar():
    ar = Edge("B", "A", 3.5, attrs={"source": "x"})

    assert ar.pair == ("A", "B")

    rev = ar.reversed()
    assert (rev.u, rev.v) == ("A", "B")
    assert rev.weight == pytest.approx(3.5)
    assert rev.attrs == {"source": "x"}

    d = ar.as_dict()
    assert d == {"u": "B", "v": "A", "weight": 3.5, "attrs": {"source": "x"}}
    json.dumps(d)  # deve ser serializável


def test_deve_ter_ids_e_adjacencia_ordenadas_de_forma_determinista():
    grafo = construir_grafo(
        [no(v) for v in "DBCA"],
        [aresta("D", "C", 2), aresta("B", "A", 1), aresta("A", "C", 3)],
    )

    assert grafo.node_ids == ["A", "B", "C", "D"]

    primeira = grafo.adjacency
    segunda = grafo.adjacency
    assert primeira == segunda  # duas leituras iguais

    for incidentes in primeira.values():
        chaves = [(e.weight, e.pair) for e in incidentes]
        assert chaves == sorted(chaves)


def test_deve_retornar_vizinhos_ordenados_e_erro_para_vertice_inexistente():
    grafo = construir_grafo_classico()

    assert grafo.neighbors("A") == ["B", "C"]

    with pytest.raises(GraphValidationError):
        grafo.neighbors("Z")


def test_deve_retornar_componentes_ordenados_e_determinista():
    grafo = construir_grafo(
        [no(v) for v in "ABCDE"],
        [aresta("D", "C", 2), aresta("B", "A", 1)],
    )

    primeira = [list(c) for c in grafo.connected_components()]
    segunda = [list(c) for c in grafo.connected_components()]

    assert primeira == segunda
    assert primeira == [["A", "B"], ["C", "D"], ["E"]]
    assert [c[0] for c in primeira] == ["A", "C", "E"]


# ---------------------------------------------------------------------------
# G-18 .. G-21
# ---------------------------------------------------------------------------

def test_deve_manter_apenas_vertices_escolhidos_e_arestas_com_as_duas_pontas_em_induced_subgraph():
    grafo = construir_grafo_classico()
    sub = grafo.induced_subgraph(["A", "B", "C"])

    assert sub.n_nodes == 3
    assert sub.node_ids == ["A", "B", "C"]
    assert sub.n_edges == 3
    assert {extremidades(e) for e in sub.edges} == {("A", "B"), ("A", "C"), ("B", "C")}
    assert all(
        u in ("A", "B", "C") and v in ("A", "B", "C")
        for u, v in (extremidades(e) for e in sub.edges)
    )


@pytest.mark.parametrize(
    "selecao",
    [["A", "Z"], [], ["Z"]],
    ids=["id-inexistente", "selecao-vazia", "apenas-id-inexistente"],
)
def test_deve_gerar_erro_em_induced_subgraph_quando_selecao_tem_id_inexistente_ou_esta_vazia(
    selecao,
):
    grafo = construir_grafo_classico()
    with pytest.raises(GraphValidationError):
        grafo.induced_subgraph(selecao)


def test_deve_retornar_um_vertice_e_zero_arestas_em_induced_subgraph_com_um_vertice():
    grafo = construir_grafo_classico()
    sub = grafo.induced_subgraph(["D"])

    assert sub.n_nodes == 1
    assert sub.n_edges == 0
    assert sub.node_ids == ["D"]


def test_deve_retornar_maior_componente_e_em_empate_o_de_menor_id():
    grafo = construir_grafo(
        [no(v) for v in "ABCDE"],
        [aresta("A", "B", 1), aresta("B", "C", 2), aresta("D", "E", 3)],
    )

    maior = grafo.largest_component()
    assert maior.n_nodes == 3
    assert set(maior.node_ids) == {"A", "B", "C"}
    assert conjunto_de_arestas(maior) == conjunto_de_arestas(grafo.largest_component())


def test_deve_escolher_componente_de_menor_id_em_empate_de_tamanho():
    grafo = construir_grafo(
        [no(v) for v in "ABCD"],
        [aresta("A", "B", 1), aresta("C", "D", 2)],
    )

    maior = grafo.largest_component()
    assert maior.n_nodes == 2
    assert set(maior.node_ids) == {"A", "B"}


# ---------------------------------------------------------------------------
# G-22 .. G-24
# ---------------------------------------------------------------------------

def test_deve_aceitar_node_edge_e_dicionarios_em_from_records_normalizar_campos_e_preservar_attrs():
    grafo = Graph.from_records(
        nodes=[Node(id="A", name="Alpha"), Node(id="B"), no("C")],
        edges=[
            Edge("A", "B", 3.0, attrs={"source": "x", "border_km": 5}),
            aresta("B", "C", 1.0, attrs={"border_km": 2}),
        ],
    )

    assert grafo.n_nodes == 3
    assert grafo.node_ids == ["A", "B", "C"]
    assert grafo.nodes["A"].name == "Alpha"
    assert grafo.n_edges == 2

    ab = achar_aresta(grafo, "A", "B")
    assert peso_da_aresta(ab) == pytest.approx(3.0)
    assert ab.attrs == {"source": "x", "border_km": 5}

    bc = achar_aresta(grafo, "B", "C")
    assert peso_da_aresta(bc) == pytest.approx(1.0)
    assert bc.attrs == {"border_km": 2}


@pytest.mark.parametrize(
    "registro",
    [
        no("A", lat="texto"),
        no("A", lat=float("nan")),
        no("A", lat=float("inf")),
        no("A", lon=float("-inf")),
    ],
    ids=["latitude-texto", "latitude-nan", "latitude-infinito", "longitude-menos-infinito"],
)
def test_deve_gerar_erro_quando_coordenada_do_no_e_invalida(registro):
    with pytest.raises(GraphValidationError):
        Graph.from_records([registro], [])


def test_deve_produzir_resultado_independente_da_ordem_de_entrada():
    nodes = [no(v) for v in "ABCDEF"]
    edges_ordem1 = [
        aresta("A", "B", 4),
        aresta("A", "C", 2),
        aresta("B", "C", 1),
        aresta("B", "D", 5),
        aresta("C", "D", 8),
        aresta("C", "E", 10),
        aresta("D", "E", 2),
        aresta("D", "F", 6),
        aresta("E", "F", 3),
    ]
    edges_ordem2 = list(reversed(edges_ordem1))
    nodes_embaralhados = list(reversed(nodes))

    g1 = construir_grafo(nodes, edges_ordem1)
    g2 = construir_grafo(nodes_embaralhados, edges_ordem2)

    assert g1.node_ids == g2.node_ids
    assert conjunto_de_arestas(g1) == conjunto_de_arestas(g2)
    assert [list(c) for c in g1.connected_components()] == [
        list(c) for c in g2.connected_components()
    ]


# ---------------------------------------------------------------------------
# U-01 .. U-08
# ---------------------------------------------------------------------------

def test_deve_inicializar_cada_no_como_propria_raiz_tamanho_1_e_contadores_zerados():
    uf = UnionFind(["A", "B", "C"])

    for node in ("A", "B", "C"):
        assert uf.parent[node] == node
        assert uf.size[node] == 1
    assert uf.find_calls == 0
    assert uf.union_calls == 0


def test_deve_retornar_proprio_no_e_incrementar_find_calls_quando_buscar_no_isolado():
    uf = UnionFind(["A", "B"])

    assert uf.find("A") == "A"
    assert uf.find_calls == 1
    assert uf.find("B") == "B"
    assert uf.find_calls == 2


def test_deve_unir_conjuntos_diferentes_retornar_true_e_somar_tamanhos():
    uf = UnionFind(["A", "B", "C"])

    assert uf.union("A", "B") is True
    assert uf.find("A") == uf.find("B")
    raiz = uf.find("A")
    assert uf.size[raiz] == 2
    assert uf.union_calls == 1


def test_deve_retornar_false_e_nao_alterar_tamanho_quando_unir_mesmo_conjunto():
    uf = UnionFind(["A", "B"])
    uf.union("A", "B")

    tamanho_antes = uf.size[uf.find("A")]
    assert uf.union("A", "B") is False
    assert uf.size[uf.find("A")] == tamanho_antes
    assert uf.union_calls == 2


def test_deve_pendurar_arvore_menor_sob_a_maior_em_uniao_por_tamanho():
    uf = UnionFind(["A", "B", "C"])
    uf.union("A", "B")
    raiz_ab = uf.find("A")
    assert uf.size[raiz_ab] == 2

    uf.union("A", "C")

    assert uf.find("C") == raiz_ab
    assert uf.parent["C"] == raiz_ab
    assert uf.size[uf.find("A")] == 3


def test_deve_comprimir_caminho_apos_find_profundo_e_ser_iterativo():
    ids = [f"N{i}" for i in range(3000)]
    uf = UnionFind(ids)

    for i in range(2999):
        uf.parent[ids[i]] = ids[i + 1]

    raiz = uf.find("N0")

    assert raiz == "N2999"
    assert uf.parent["N0"] == "N2999"
    assert uf.find_calls >= 1


def test_deve_refletir_unioes_em_connected_e_component_size_e_contar_finds():
    uf = UnionFind(["A", "B", "C"])

    antes = uf.find_calls
    assert uf.connected("A", "B") is False
    assert uf.find_calls == antes + 2

    uf.union("A", "B")
    assert uf.connected("A", "B") is True
    assert uf.component_size("A") == 2
    assert uf.component_size("B") == 2
    assert uf.component_size("C") == 1


def test_deve_permanecer_consistente_com_contadores_coerentes_em_sequencia_grande_de_unioes_e_finds():
    ids = [f"V{i:03d}" for i in range(100)]
    uf = UnionFind(ids)
    rnd = random.Random(42)

    n_unioes_tentadas = 600
    for _ in range(n_unioes_tentadas):
        a, b = rnd.sample(ids, 2)
        uf.union(a, b)

    assert uf.union_calls == n_unioes_tentadas
    assert uf.find_calls == 2 * n_unioes_tentadas

    raizes = [node for node in ids if uf.parent[node] == node]
    assert sum(uf.size[r] for r in raizes) == len(ids)
    assert all(uf.size[r] >= 1 for r in raizes)

    for _ in range(200):
        a, b = rnd.sample(ids, 2)
        assert uf.connected(a, b) == (uf.find(a) == uf.find(b))
        assert uf.component_size(a) == uf.size[uf.find(a)]


def test_construtor_direto_cobre_validacoes_e_normalizacao_de_arestas():
    """G-01/G-03/G-06/G-08/G-14: validações e normalização no construtor direto."""
    # Arrange: vértice com id vazio é rejeitado
    with pytest.raises(GraphValidationError, match="id não vazio"):
        Graph([Node(id="", name="", lat=None, lon=None)], [])

    # Arrange: aresta com peso não numérico é rejeitada
    with pytest.raises(GraphValidationError, match="Peso inválido"):
        Graph(
            [Node(id="A", name="A", lat=None, lon=None), Node(id="B", name="B", lat=None, lon=None)],
            [Edge("A", "B", float("nan"))],
        )

    # Act: laço é ignorado e não entra no grafo
    sem_laco = Graph(
        [Node(id="A", name="A", lat=None, lon=None)],
        [Edge("A", "A", 1.0)],
    )
    assert sem_laco.n_edges == 0

    # Act: duplicata em qualquer orientação mantém apenas a primeira aresta
    com_duplicata = Graph(
        [Node(id="A", name="A", lat=None, lon=None), Node(id="B", name="B", lat=None, lon=None)],
        [Edge("A", "B", 1.0), Edge("B", "A", 2.0)],
    )
    assert com_duplicata.n_edges == 1
    assert com_duplicata.edges[0].weight == 1.0

    # Act: aresta invertida é normalizada para u <= v
    invertida = Graph(
        [Node(id="A", name="A", lat=None, lon=None), Node(id="B", name="B", lat=None, lon=None)],
        [Edge("B", "A", 3.0)],
    )
    assert (invertida.edges[0].u, invertida.edges[0].v) == ("A", "B")

    # Act: from_records rejeita extremos que não são strings
    with pytest.raises(GraphValidationError, match="Extremos de aresta inválidos"):
        Graph.from_records(
            [{"id": "A", "name": "A", "lat": None, "lon": None}],
            [{"u": 1, "v": "A", "weight": 1.0}],
        )
