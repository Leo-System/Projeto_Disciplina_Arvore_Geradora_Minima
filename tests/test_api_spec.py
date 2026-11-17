"""Testes de integração da API HTTP com TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.uploads import MAX_UPLOAD_BYTES


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_health_responde_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cities_devolve_645_municipios_com_vizinhos(client: TestClient) -> None:
    response = client.get("/api/v1/cities")

    assert response.status_code == 200
    cities = response.json()["cities"]
    assert len(cities) == 645
    bauru = next(city for city in cities if city["id"] == "3506003")
    assert bauru["name"] == "Bauru"
    assert bauru["neighbors"]
    assert isinstance(bauru["lat"], float)


def test_presets_lista_as_cinco_instancias(client: TestClient) -> None:
    response = client.get("/api/v1/presets")

    assert response.status_code == 200
    presets = response.json()["presets"]
    assert [preset["id"] for preset in presets] == [
        "p1-bauru-vizinhos",
        "p2-regiao-bauru",
        "p3-estado-sp",
        "p4-regioes-separadas",
        "p5-litoral-norte",
    ]
    by_id = {preset["id"]: preset for preset in presets}
    assert by_id["p3-estado-sp"]["n_nodes"] == 644
    assert by_id["p3-estado-sp"]["n_edges"] == 1832
    assert by_id["p4-regioes-separadas"]["n_components"] == 2


def test_preset_detail_devolve_grafo_completo(client: TestClient) -> None:
    response = client.get("/api/v1/presets/p1-bauru-vizinhos")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "p1-bauru-vizinhos"
    assert len(payload["graph"]["nodes"]) == 8
    assert len(payload["graph"]["edges"]) == 15
    assert payload["graph"]["stats"]["n_components"] == 1


def test_preset_inexistente_devolve_404_legivel(client: TestClient) -> None:
    response = client.get("/api/v1/presets/p9-nao-existe")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert "não encontrada" in error["message"]


def test_preset_p3_lista_ilhabela_como_descartada(client: TestClient) -> None:
    response = client.get("/api/v1/presets/p3-estado-sp")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["graph"]["nodes"]) == 644
    assert [item["id"] for item in payload["graph"]["discarded"]] == ["3520400"]
    assert any("Ilhabela" in warning for warning in payload["graph"]["warnings"])


def test_run_com_preset_p1_retorna_ambos_e_comparacao(client: TestClient) -> None:
    response = client.post(
        "/api/v1/run",
        json={
            "preset_id": "p1-bauru-vizinhos",
            "algorithm": "both",
            "trace": True,
            "verify": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kruskal"] is not None
    assert payload["prim"] is not None
    assert payload["kruskal"]["total_cost"] == pytest.approx(
        payload["prim"]["total_cost"], abs=1e-6
    )
    assert len(payload["kruskal"]["edges"]) == 7
    assert payload["kruskal"]["trace"]
    assert payload["comparison"]["same_cost"] is True
    assert payload["comparison"]["is_consistent"] is True
    assert payload["verification"]["kruskal"]["is_valid"] is True
    assert payload["verification"]["prim"]["is_valid"] is True
    assert payload["graph_stats"]["n_nodes"] == 8


def test_run_com_p3_sem_trace_confere_referencia(client: TestClient) -> None:
    response = client.post(
        "/api/v1/run",
        json={
            "preset_id": "p3-estado-sp",
            "algorithm": "both",
            "trace": False,
            "verify": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kruskal"]["total_cost"] == pytest.approx(9034.325, abs=1.0)
    assert payload["prim"]["total_cost"] == pytest.approx(9034.325, abs=1.0)
    assert len(payload["kruskal"]["edges"]) == 643
    assert payload["kruskal"]["trace"] is None
    assert payload["graph_stats"]["n_nodes"] == 644
    assert payload["graph_stats"]["n_edges"] == 1832
    assert payload["graph_stats"]["n_components"] == 1


def test_build_graph_e_run_com_grafo_montado(client: TestClient) -> None:
    cities = client.get("/api/v1/cities").json()["cities"]
    bauru = next(city for city in cities if city["id"] == "3506003")
    neighbor = bauru["neighbors"][0]

    build_response = client.post(
        "/api/v1/graph/build",
        json={"city_ids": ["3506003", neighbor], "include_manual": True},
    )

    assert build_response.status_code == 200
    graph = build_response.json()
    assert len(graph["nodes"]) == 2
    assert graph["stats"]["n_edges"] == 1

    run_response = client.post(
        "/api/v1/run",
        json={
            "graph": graph,
            "algorithm": "prim",
            "start_vertex": "3506003",
            "trace": False,
            "verify": True,
        },
    )

    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["kruskal"] is None
    assert payload["prim"] is not None
    assert len(payload["prim"]["edges"]) == 1
    assert payload["comparison"]["same_cost"] is None
    assert payload["verification"]["prim"]["is_valid"] is True


def test_build_graph_com_selecao_insuficiente_devolve_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/graph/build",
        json={"city_ids": ["3506003"], "include_manual": True},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "ao menos 2" in error["message"]


def test_build_graph_com_codigo_inexistente_devolve_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/graph/build",
        json={"city_ids": ["3506003", "9999999"], "include_manual": True},
    )

    assert response.status_code == 422
    assert "inexistente" in response.json()["error"]["message"]


def test_build_graph_com_conexao_automatica(client: TestClient) -> None:
    response = client.post(
        "/api/v1/graph/build",
        json={
            "city_ids": ["3506003", "3550704"],
            "include_manual": True,
            "connect_components": True,
        },
    )

    assert response.status_code == 200
    graph = response.json()
    assert graph["stats"]["n_components"] == 1
    assert len(graph["nodes"]) > 2
    assert any("adicionado" in warning for warning in graph["warnings"])


def test_build_graph_sem_connect_components_usa_padrao_false(client: TestClient) -> None:
    cities = client.get("/api/v1/cities").json()["cities"]
    bauru = next(city for city in cities if city["id"] == "3506003")
    sao_sebastiao = next(city for city in cities if city["id"] == "3550704")

    response = client.post(
        "/api/v1/graph/build",
        json={"city_ids": [bauru["id"], sao_sebastiao["id"]], "include_manual": True},
    )

    assert response.status_code == 200
    graph = response.json()
    # Sem a opção, Bauru e São Sebastião permanecem em componentes separados.
    assert graph["stats"]["n_components"] == 2


def test_run_sem_grafo_nem_preset_devolve_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/run",
        json={"algorithm": "both", "trace": False, "verify": True},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "exatamente um" in " ".join(error["details"])


def test_run_com_vertice_inicial_inexistente_devolve_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/run",
        json={
            "preset_id": "p1-bauru-vizinhos",
            "algorithm": "prim",
            "start_vertex": "0000000",
            "trace": False,
            "verify": False,
        },
    )

    assert response.status_code == 422
    assert "inexistente" in response.json()["error"]["message"]


def test_upload_csv_valido_pela_api(client: TestClient) -> None:
    content = b"origem,destino,peso\nA,B,4\nA,C,2\nB,C,1\n"

    response = client.post(
        "/api/v1/graph/upload",
        files={"file": ("grafo.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    graph = response.json()["graph"]
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 3
    assert graph["stats"]["n_components"] == 1


def test_upload_invalido_pela_api_devolve_detalhes(client: TestClient) -> None:
    response = client.post(
        "/api/v1/graph/upload",
        files={"file": ("grafo.csv", b"origem,destino,peso\nA,B,abc\n", "text/csv")},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]
    assert any("linha 2" in detail.lower() for detail in error["details"])


def test_upload_acima_do_limite_pela_api_devolve_413(client: TestClient) -> None:
    content = b"x" * (MAX_UPLOAD_BYTES + 1)

    response = client.post(
        "/api/v1/graph/upload",
        files={"file": ("grande.csv", content, "text/csv")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_benchmark_pela_api_devolve_sete_tamanhos(client: TestClient) -> None:
    response = client.post("/api/v1/benchmark", json={"runs": 1})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rows"]) == 8
    assert payload["meta"]["preset_id"] == "p3-estado-sp"
    assert payload["meta"]["start_city_name"] == "Bauru"
    assert payload["meta"]["runs"] == 1
    for row in payload["rows"]:
        assert row["n_nodes"] > 0
        assert row["n_edges"] >= 0
        assert row["kruskal_ms"] >= 0
        assert row["prim_ms"] >= 0
        assert row["kruskal_p25_ms"] <= row["kruskal_p75_ms"]
        assert row["prim_p25_ms"] <= row["prim_p75_ms"]


def test_benchmark_com_runs_fora_do_limite_devolve_422(client: TestClient) -> None:
    response = client.post("/api/v1/benchmark", json={"runs": 101})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
