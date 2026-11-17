"""Testes das instâncias prontas, incluindo o caso grande e a floresta."""

from __future__ import annotations

import pytest

from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.prim import prim
from backend.app.algorithms.verify import verify_forest
from backend.app.data_loader import load_cities
from backend.app.errors import NotFoundError
from backend.app.services.presets import city_id_by_name, get_preset, get_presets

CIDADE_BAURU = "3506003"
CIDADE_ILHABELA = "3520400"
CIDADE_SAO_SEBASTIAO = "3550704"


def test_cinco_presets_com_tamanhos_esperados() -> None:
    presets = {preset.id: preset for preset in get_presets()}

    assert list(presets) == [
        "p1-bauru-vizinhos",
        "p2-regiao-bauru",
        "p3-estado-sp",
        "p4-regioes-separadas",
        "p5-litoral-norte",
    ]

    p1 = presets["p1-bauru-vizinhos"]
    assert (p1.graph.n_nodes, p1.graph.n_edges) == (8, 15)
    assert CIDADE_BAURU in p1.graph.nodes

    p2 = presets["p2-regiao-bauru"]
    assert (p2.graph.n_nodes, p2.graph.n_edges) == (109, 295)

    p3 = presets["p3-estado-sp"]
    assert (p3.graph.n_nodes, p3.graph.n_edges) == (644, 1832)
    assert p3.include_manual is False

    p4 = presets["p4-regioes-separadas"]
    assert (p4.graph.n_nodes, p4.graph.n_edges) == (20, 37)
    assert len(p4.graph.connected_components()) == 2

    p5 = presets["p5-litoral-norte"]
    assert (p5.graph.n_nodes, p5.graph.n_edges) == (4, 3)
    assert p5.include_manual is True


def test_presets_usam_vertices_do_catalogo_real() -> None:
    catalog_ids = {city.id for city in load_cities()}

    for preset in get_presets():
        assert set(preset.graph.node_ids) <= catalog_ids
        assert preset.summary()["n_nodes"] == preset.graph.n_nodes
        assert preset.summary()["n_edges"] == preset.graph.n_edges


def test_p3_mantem_maior_componente_e_descarta_ilhabela() -> None:
    preset = get_preset("p3-estado-sp")

    assert [item["id"] for item in preset.discarded] == [CIDADE_ILHABELA]
    assert "Ilhabela" in preset.discarded[0]["name"]
    assert "Ilhabela" in " ".join(preset.warnings)
    assert all(
        edge.attrs.get("source") != "manual" for edge in preset.graph.edges
    )


def test_p3_kruskal_e_prim_chegam_ao_mesmo_custo_de_referencia() -> None:
    preset = get_preset("p3-estado-sp")
    graph = preset.graph

    result_kruskal = kruskal(graph)
    result_prim = prim(graph, start_vertex=CIDADE_BAURU)

    assert len(result_kruskal.edges) == 643
    assert len(result_prim.edges) == 643
    assert result_kruskal.total_cost == pytest.approx(9034.325, abs=1.0)
    assert result_prim.total_cost == pytest.approx(result_kruskal.total_cost, abs=1e-6)

    for result in (result_kruskal, result_prim):
        verification = verify_forest(graph, result)
        assert verification.is_valid is True
        assert verification.is_forest is True
        assert verification.cycle_property is True


def test_p4_produz_floresta_com_n_menos_c_arestas() -> None:
    preset = get_preset("p4-regioes-separadas")
    graph = preset.graph
    components = len(graph.connected_components())

    assert components == 2
    for result in (kruskal(graph), prim(graph, start_vertex=CIDADE_BAURU)):
        assert result.n_components == components
        assert result.is_forest is True
        assert len(result.edges) == graph.n_nodes - components == 18
        assert verify_forest(graph, result).is_valid is True


def test_p5_inclui_a_ligacao_manual_por_balsa() -> None:
    preset = get_preset("p5-litoral-norte")
    manual = [edge for edge in preset.graph.edges if edge.attrs.get("source") == "manual"]

    assert len(manual) == 1
    assert {manual[0].u, manual[0].v} == {CIDADE_ILHABELA, CIDADE_SAO_SEBASTIAO}


def test_busca_de_cidade_por_nome_ignora_acentos_e_caixa() -> None:
    assert city_id_by_name("Bauru") == CIDADE_BAURU
    assert city_id_by_name("sao sebastiao") == CIDADE_SAO_SEBASTIAO
    assert city_id_by_name("São Sebastião") == CIDADE_SAO_SEBASTIAO


def test_preset_inexistente_gera_not_found() -> None:
    with pytest.raises(NotFoundError):
        get_preset("p9-inexistente")

    with pytest.raises(NotFoundError):
        city_id_by_name("Município Que Não Existe")
