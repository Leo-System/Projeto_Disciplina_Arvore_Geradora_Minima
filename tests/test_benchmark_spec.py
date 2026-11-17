"""Testes do serviço de análise de tempo (benchmark)."""

from __future__ import annotations

import math

import pytest

from backend.app.errors import NotFoundError
from backend.app.services.benchmark import run_benchmark
from conftest import gerar_grafo_conexo


def test_benchmark_devolve_tamanhos_crescentes_e_tempos_finitos() -> None:
    payload = run_benchmark(runs=1)

    rows = payload["rows"]
    assert len(rows) == 8
    assert [row["n_edges"] for row in rows] == sorted(row["n_edges"] for row in rows)
    assert rows[-1]["n_nodes"] == 644
    assert rows[-1]["n_edges"] == 1832

    for row in rows:
        for field in (
            "kruskal_ms",
            "kruskal_p25_ms",
            "kruskal_p75_ms",
            "prim_ms",
            "prim_p25_ms",
            "prim_p75_ms",
        ):
            assert math.isfinite(row[field])
            assert row[field] >= 0
        assert row["kruskal_p25_ms"] <= row["kruskal_ms"] <= row["kruskal_p75_ms"]
        assert row["prim_p25_ms"] <= row["prim_ms"] <= row["prim_p75_ms"]


def test_benchmark_informa_metadados_da_instancia() -> None:
    meta = run_benchmark(runs=1)["meta"]

    assert meta["preset_id"] == "p3-estado-sp"
    assert "São Paulo" in meta["preset_name"]
    assert meta["start_city"] == "3506003"
    assert meta["start_city_name"] == "Bauru"
    assert meta["runs"] == 1
    assert "milissegundos" in meta["note"]


def test_benchmark_limita_runs_ao_intervalo_valido() -> None:
    assert run_benchmark(runs=0)["meta"]["runs"] == 1
    assert run_benchmark(runs=-10)["meta"]["runs"] == 1


def test_benchmark_com_preset_inexistente_gera_not_found() -> None:
    with pytest.raises(NotFoundError):
        run_benchmark(preset_id="p9-nao-existe", runs=1)


def test_benchmark_com_cidade_inicial_fora_da_instancia_gera_not_found() -> None:
    with pytest.raises(NotFoundError):
        run_benchmark(start_city_name="Município Que Não Existe", runs=1)


# ---------------------------------------------------------------------------
# Grafo do usuário: subgrafos crescentes
# ---------------------------------------------------------------------------


def test_benchmark_do_grafo_do_usuario_gera_linhas_crescentes_ate_o_grafo_completo() -> None:
    # Arrange: grafo conexo com 60 vértices; o passo é ceil(60 / 12) = 5.
    grafo, _ = gerar_grafo_conexo(60, extras=30, seed=7)

    # Act
    payload = run_benchmark(graph=grafo, runs=1)

    # Assert
    rows = payload["rows"]
    assert len(rows) > 1
    nos = [row["n_nodes"] for row in rows]
    arestas = [row["n_edges"] for row in rows]
    assert nos == sorted(nos)
    assert arestas == sorted(arestas)
    assert len(set(nos)) == len(nos)
    assert nos[0] >= 2
    assert rows[-1]["n_nodes"] == grafo.n_nodes
    assert rows[-1]["n_edges"] == grafo.n_edges
    for row in rows:
        assert row["kruskal_p25_ms"] <= row["kruskal_ms"] <= row["kruskal_p75_ms"]
        assert row["prim_p25_ms"] <= row["prim_ms"] <= row["prim_p75_ms"]


def test_benchmark_do_grafo_do_usuario_tem_meta_do_grafo_e_passo_documentado() -> None:
    # Arrange
    grafo, _ = gerar_grafo_conexo(30, extras=10, seed=3)

    # Act
    meta = run_benchmark(graph=grafo, runs=2)["meta"]

    # Assert
    assert meta["preset_id"] == "user-graph"
    assert meta["preset_name"] == "Grafo do usuário"
    assert meta["start_city"] == ""
    assert meta["start_city_name"] == ""
    assert meta["runs"] == 2
    assert "subgrafos induzidos crescentes" in meta["note"]
    assert "passos de" in meta["note"]


def test_benchmark_do_grafo_do_usuario_com_um_unico_vertice_devolve_uma_linha() -> None:
    # Arrange
    grafo, _ = gerar_grafo_conexo(1, extras=0, seed=1)

    # Act
    payload = run_benchmark(graph=grafo, runs=1)

    # Assert
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["n_nodes"] == 1
    assert payload["rows"][0]["n_edges"] == 0
