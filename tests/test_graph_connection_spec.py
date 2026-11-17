"""Testes de especificação para conexão automática da seleção (feature connect_components)."""

from __future__ import annotations

from unittest import mock

import pytest

from backend.app.errors import ValidationError
from backend.app.services.graph_selection import build_from_city_ids
from backend.app.data_loader import load_graph

BAURU = "3506003"
SAO_SEBASTIAO = "3550704"
ILHABELA = "3520400"


def test_opcao_desligada_preserva_comportamento_atual():
    """S-11: com connect_components=False, grafo de duas cidades distantes fica com 2 componentes."""
    built = build_from_city_ids(
        [BAURU, SAO_SEBASTIAO],
        include_manual=True,
        connect_components=False,
    )
    assert len(built.graph.connected_components()) == 2
    assert any("desconexo" in w.lower() for w in built.warnings)


def test_duas_cidades_distantes_com_opcao_ligada_viram_um_componente():
    """S-12: com connect_components=True, Bauru e São Sebastião formam um único componente."""
    built = build_from_city_ids(
        [BAURU, SAO_SEBASTIAO],
        include_manual=True,
        connect_components=True,
    )
    assert len(built.graph.connected_components()) == 1
    assert BAURU in built.graph.node_ids
    assert SAO_SEBASTIAO in built.graph.node_ids
    assert built.graph.n_nodes > 2
    assert any("adicionado" in w for w in built.warnings)


def test_selecao_ja_conexa_nao_adiciona_ninguem():
    """S-13: seleção já conexa não adiciona cidades nem aviso de adicionados."""
    full = load_graph(include_manual=True)
    neighbor = full.neighbors(BAURU)[0]
    built = build_from_city_ids(
        [BAURU, neighbor],
        include_manual=True,
        connect_components=True,
    )
    assert built.graph.n_nodes == 2
    assert built.graph.n_edges == 1
    assert not any("adicionado" in w for w in built.warnings)


def test_balsa_automatica():
    """S-14: com include_manual=False e cidades em componentes separados, balsa é incluída automaticamente."""
    built = build_from_city_ids(
        [ILHABELA, BAURU],
        include_manual=False,
        connect_components=True,
    )
    assert len(built.graph.connected_components()) == 1
    assert any(
        edge.attrs.get("source") == "manual" for edge in built.graph.edges
    )
    assert any("automaticamente" in w for w in built.warnings)


def test_balsa_nao_usada_quando_nao_necessaria():
    """S-15: duas cidades do componente principal com include_manual=False não usam balsa."""
    full = load_graph(include_manual=False)
    # Duas cidades vizinhas do componente principal (sem balsa).
    cidade_a = BAURU
    vizinha = full.neighbors(cidade_a)[0]
    built = build_from_city_ids(
        [cidade_a, vizinha],
        include_manual=False,
        connect_components=True,
    )
    manual_edges = [e for e in built.graph.edges if e.attrs.get("source") == "manual"]
    assert not manual_edges, "Balsa não deveria ser usada quando não necessária"


def test_aviso_limita_lista_a_20_nomes():
    """S-16: aviso de cidades adicionadas limita a 20 nomes com 'e mais N'."""
    built = build_from_city_ids(
        [BAURU, SAO_SEBASTIAO],
        include_manual=True,
        connect_components=True,
    )
    adicionados = [w for w in built.warnings if "adicionado" in w]
    assert adicionados, "Esperava aviso de cidades adicionadas"
    mensagem = adicionados[0]
    if "e mais" in mensagem:
        assert "municípios foram adicionados" in mensagem
    # Verifica singular/plural coerente
    if "1 município foi adicionado" in mensagem:
        assert "e mais" not in mensagem


def test_determinismo():
    """S-17: duas chamadas iguais produzem o mesmo conjunto de vértices e arestas."""
    args = dict(city_ids=[BAURU, SAO_SEBASTIAO], include_manual=True, connect_components=True)
    primeiro = build_from_city_ids(**args)
    segundo = build_from_city_ids(**args)
    assert primeiro.graph.node_ids == segundo.graph.node_ids
    pares_um = sorted((min(e.u, e.v), max(e.u, e.v)) for e in primeiro.graph.edges)
    pares_dois = sorted((min(e.u, e.v), max(e.u, e.v)) for e in segundo.graph.edges)
    assert pares_um == pares_dois


def test_caso_impossivel_erro_defensivo(monkeypatch):
    """S-18: grafo sem arestas mesmo com balsa -> ValidationError."""

    def falso_grafo(include_manual=True):
        return load_graph.__wrapped__(include_manual=True) if hasattr(load_graph, "__wrapped__") else None

    # Monta um grafo com dois nós válidos e nenhuma aresta.
    from backend.app.algorithms.graph import Graph, Node

    grafo_vazio = Graph(
        [Node(id=BAURU, name="Bauru"), Node(id=SAO_SEBASTIAO, name="São Sebastião")],
        [],
    )

    with mock.patch("backend.app.services.graph_selection.load_graph", return_value=grafo_vazio):
        with pytest.raises(ValidationError):
            build_from_city_ids(
                [BAURU, SAO_SEBASTIAO],
                include_manual=True,
                connect_components=True,
            )


def test_menos_de_duas_cidades_erro_antes_da_expansao():
    """S-19: menos de 2 cidades gera ValidationError antes de qualquer expansão."""
    with pytest.raises(ValidationError) as exc:
        build_from_city_ids([BAURU], connect_components=True)
    assert "ao menos 2" in str(exc.value)


def test_id_inexistente_erro_antes_da_expansao():
    """S-20: ID inexistente gera ValidationError antes de qualquer expansão."""
    with pytest.raises(ValidationError) as exc:
        build_from_city_ids([BAURU, "9999999"], connect_components=True)
    assert "inexistente" in str(exc.value).lower()
