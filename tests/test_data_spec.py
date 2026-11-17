"""Testes dos dados processados e da referência de otimalidade."""

from __future__ import annotations

import math

import pytest

from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.verify import verify_forest
from backend.app.data_loader import load_cities, load_edges, load_graph

CIDADE_ILHABELA = "3520400"
CIDADE_SAO_SEBASTIAO = "3550704"


def test_catalogo_tem_645_municipios_paulistas_unicos() -> None:
    cities = load_cities()

    assert len(cities) == 645
    assert len({city.id for city in cities}) == 645
    for city in cities:
        assert len(city.id) == 7
        assert city.id.isdigit()
        assert city.id.startswith("35")
        assert city.name.strip()
        assert math.isfinite(city.lat)
        assert math.isfinite(city.lon)


def test_arestas_processadas_tem_1832_divisas_e_uma_ligacao_manual() -> None:
    edges = load_edges()

    assert len(edges) == 1833
    assert sum(1 for edge in edges if edge.source == "divisa") == 1832
    manuais = [edge for edge in edges if edge.source == "manual"]
    assert len(manuais) == 1
    assert {manuais[0].u, manuais[0].v} == {CIDADE_ILHABELA, CIDADE_SAO_SEBASTIAO}
    assert len({(edge.u, edge.v) for edge in edges}) == len(edges)
    assert all(edge.u < edge.v for edge in edges)
    assert all(math.isfinite(edge.dist_km) and edge.dist_km > 0 for edge in edges)
    assert all(
        edge.border_km is None or (math.isfinite(edge.border_km) and edge.border_km >= 0)
        for edge in edges
    )


def test_divisas_curtas_somam_71_pares() -> None:
    short_edges = [
        edge
        for edge in load_edges()
        if edge.source == "divisa" and edge.short_border
    ]

    assert len(short_edges) == 71
    assert sum(1 for edge in short_edges if edge.border_km == 0) == 54


def test_grafo_de_divisas_tem_ilhabela_isolada_e_644_no_maior_componente() -> None:
    graph = load_graph(include_manual=False)
    components = graph.connected_components()

    assert graph.n_nodes == 645
    assert graph.n_edges == 1832
    assert len(components) == 2
    assert [CIDADE_ILHABELA] in components
    assert len(graph.largest_component().node_ids) == 644


def test_grafo_com_manual_fica_conexo_e_com_1833_arestas() -> None:
    graph = load_graph(include_manual=True)

    assert graph.n_nodes == 645
    assert graph.n_edges == 1833
    assert len(graph.connected_components()) == 1
    manual = [edge for edge in graph.edges if edge.attrs.get("source") == "manual"]
    assert len(manual) == 1
    assert {manual[0].u, manual[0].v} == {CIDADE_ILHABELA, CIDADE_SAO_SEBASTIAO}


def test_mst_do_maior_componente_bate_com_a_referencia() -> None:
    graph = load_graph(include_manual=False).largest_component()
    result = kruskal(graph)

    assert graph.n_nodes == 644
    assert graph.n_edges == 1832
    assert len(result.edges) == 643
    assert result.n_components == 1
    assert result.total_cost == pytest.approx(9034.325, abs=1.0)

    verification = verify_forest(graph, result)
    assert verification.performed is True
    assert verification.is_forest is True
    assert verification.cycle_property is True
    assert verification.is_valid is True


def test_grafia_exibida_e_a_da_planilha_do_ibge() -> None:
    names = {city.name for city in load_cities()}

    assert {"Biritiba Mirim", "Florínea", "Itaoca"} <= names
    assert "Biritiba-Mirim" not in names
    assert "Florínia" not in names
    assert "Itaóca" not in names
