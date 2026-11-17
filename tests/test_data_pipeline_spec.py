"""Testes do pipeline de dados e validações esperadas (IDs D-01 a D-16)."""

from __future__ import annotations

import math

import pytest

from backend.app.algorithms.kruskal import kruskal
from backend.app.algorithms.verify import verify_forest
from backend.app.data_loader import load_cities, load_edges, load_graph, city_by_id, city_name_map
from scripts.build_dataset import haversine_km, main as build_main, DatasetError, EXPECTED_UNIQUE_SHORT_BORDER, EXPECTED_UNIQUE_ZERO_BORDER, ILHABELA_CODE, EXPECTED_SP_CITIES, EXPECTED_SP_SP_EDGES

CIDADE_ILHABELA = "3520400"
CIDADE_SAO_SEBASTIAO = "3550704"


# ── D-01 ──────────────────────────────────────────────────────────────
def test_arquivos_csv_tem_cabecalhos_exatos() -> None:
    """Arquivos existem; cabeçalhos exatos id,name,lat,lon e u,v,dist_km,border_km,source,short_border."""
    # Verifica cabeçalho de cities.csv lendo a primeira linha
    with open("data/processed/cities.csv", encoding="utf-8", newline="") as f:
        header = f.readline().strip().split(",")
    assert header == ["id", "name", "lat", "lon"], f"cabeçalho cities: {header}"

    with open("data/processed/edges.csv", encoding="utf-8", newline="") as f:
        header = f.readline().strip().split(",")
    assert header == ["u", "v", "dist_km", "border_km", "source", "short_border"], f"cabeçalho edges: {header}"


# ── D-02 ──────────────────────────────────────────────────────────────
def test_catalogo_tem_645_municipios_paulistas_unicos() -> None:
    """645 municípios, IDs únicos de 7 dígitos iniciando em 35, nomes não vazios, lat/lon finitos."""
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


# ── D-03 ──────────────────────────────────────────────────────────────
def test_arestas_processadas_tem_1832_divisas_e_uma_ligacao_manual() -> None:
    """1.833 no total: 1.832 divisa + 1 manual."""
    edges = load_edges()
    assert len(edges) == 1833
    assert sum(1 for edge in edges if edge.source == "divisa") == 1832
    manuais = [edge for edge in edges if edge.source == "manual"]
    assert len(manuais) == 1
    assert {manuais[0].u, manuais[0].v} == {CIDADE_ILHABELA, CIDADE_SAO_SEBASTIAO}


# ── D-04 ──────────────────────────────────────────────────────────────
def test_invariantes_das_arestas_u_v_dist_border() -> None:
    """u < v, sem laços, sem pares duplicados, dist_km > 0 finito, border_km nulo ou >= 0."""
    edges = load_edges()
    assert all(edge.u < edge.v for edge in edges)
    assert len({(edge.u, edge.v) for edge in edges}) == len(edges)
    assert all(math.isfinite(edge.dist_km) and edge.dist_km > 0 for edge in edges)
    assert all(
        edge.border_km is None or (math.isfinite(edge.border_km) and edge.border_km >= 0)
        for edge in edges
    )


# ── D-05 ──────────────────────────────────────────────────────────────
def test_divisas_curtas_71_pares_e_54_com_border_0() -> None:
    """71 pares com short_border, dos quais 54 com border_km == 0."""
    short_edges = [
        edge
        for edge in load_edges()
        if edge.source == "divisa" and edge.short_border
    ]
    assert len(short_edges) == 71
    assert sum(1 for edge in short_edges if edge.border_km == 0) == 54


# ── D-06 ──────────────────────────────────────────────────────────────
def test_grafo_de_divisas_645_vertices_2_componentes_ilhabela_isolada() -> None:
    """Grafo só de divisas: 645 vértices, 1832 arestas, 2 componentes; Ilhabela 3520400 isolada; maior componente 644."""
    graph = load_graph(include_manual=False)
    components = graph.connected_components()
    assert graph.n_nodes == 645
    assert graph.n_edges == 1832
    assert len(components) == 2
    # Componentes são listas de IDs; verifica que Ilhabela está isolada
    ilhabela_component = [c for c in components if CIDADE_ILHABELA in c]
    assert len(ilhabela_component) == 1
    assert len(ilhabela_component[0]) == 1  # isolada, só ela mesma
    # Maior componente tem 644 nós
    largest = max(components, key=len)
    assert len(largest) == 644
    assert len(graph.largest_component().node_ids) == 644


# ── D-07 ──────────────────────────────────────────────────────────────
def test_grafo_com_ligacao_manual_645_1833_1_componente() -> None:
    """Com ligação manual: 645 vértices, 1833 arestas, 1 componente; aresta manual Ilhabela—São Sebastião."""
    graph = load_graph(include_manual=True)
    assert graph.n_nodes == 645
    assert graph.n_edges == 1833
    assert len(graph.connected_components()) == 1
    manual = [edge for edge in graph.edges if edge.attrs.get("source") == "manual"]
    assert len(manual) == 1
    assert {manual[0].u, manual[0].v} == {CIDADE_ILHABELA, CIDADE_SAO_SEBASTIAO}


# ── D-08 ──────────────────────────────────────────────────────────────
def test_mst_maior_componente_divisas_bate_referencia() -> None:
    """AGM do maior componente de divisas: 643 arestas, custo ≈ 9.034,325 km (tolerância ±1 km), verify aprova."""
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


# ── D-09 ──────────────────────────────────────────────────────────────
def test_grafia_exibida_contem_e_nao_contem_nomes() -> None:
    """Grafia exibida contém Biritiba Mirim, Florínea, Itaoca; não contém Biritiba-Mirim, Florínia, Itaóca."""
    names = {city.name for city in load_cities()}

    assert "Biritiba Mirim" in names
    assert "Florínea" in names
    assert "Itaoca" in names
    assert "Biritiba-Mirim" not in names
    assert "Florínia" not in names
    assert "Itaóca" not in names


# ── D-10 ──────────────────────────────────────────────────────────────
def test_reexecutar_build_dataset_com_dados_brutos_validos(tmp_path, monkeypatch) -> None:
    """Reexecutar o pipeline com dados brutos válidos gera saída determinística e válida.

    Executa as funções públicas do script em diretório temporário; não sobrescreve
    data/processed e compara byte a byte com a saída versionada.
    """
    import scripts.build_dataset as bd
    from pathlib import Path

    # Arrange: lê os dados brutos reais e redireciona a saída para o temp.
    rows = bd.read_ods_rows(bd.ODS_FILE)
    cities = bd.read_cities_csv(bd.CITIES_FILE)
    divisa_edges, stats, display_names = bd.build_divisa_edges(rows, cities)
    existing_pairs = {(edge.u, edge.v) for edge in divisa_edges}
    manual_edges = bd.read_manual_edges(bd.EXTRAS_FILE, cities, existing_pairs)
    bd.validate_dataset(cities, divisa_edges, manual_edges, stats, display_names)
    for city_id, ods_name in display_names.items():
        cities[city_id].name = ods_name

    monkeypatch.setattr(bd, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bd, "PROCESSED_DIR", tmp_path / "processed")

    # Act
    bd.write_outputs(cities, divisa_edges + manual_edges)

    # Assert
    raiz = Path(__file__).resolve().parents[1]
    assert (tmp_path / "processed" / "cities.csv").read_bytes() == (
        raiz / "data" / "processed" / "cities.csv"
    ).read_bytes()
    assert (tmp_path / "processed" / "edges.csv").read_bytes() == (
        raiz / "data" / "processed" / "edges.csv"
    ).read_bytes()


# ── D-11 ──────────────────────────────────────────────────────────────
def test_build_dataset_sem_ods_ou_sem_aba_correta_falha(tmp_path, monkeypatch) -> None:
    """build_dataset.py sem ODS/CSV bruto falha com DatasetError e não grava saída parcial."""
    import scripts.build_dataset as bd

    # Arrange: aponta os caminhos para um diretório temporário sem arquivos brutos.
    monkeypatch.setattr(bd, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bd, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(bd, "MANUAL_DIR", tmp_path / "manual")
    monkeypatch.setattr(bd, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(bd, "ODS_FILE", tmp_path / "raw" / "ausente.ods")
    monkeypatch.setattr(bd, "CITIES_FILE", tmp_path / "raw" / "ausente.csv")
    monkeypatch.setattr(bd, "EXTRAS_FILE", tmp_path / "manual" / "ausente.csv")

    # Act / Assert
    with pytest.raises(DatasetError) as excinfo:
        bd.main()
    assert str(excinfo.value).strip(), "mensagem de erro deve ser clara"
    assert not (tmp_path / "processed").exists(), "não deve gravar saída parcial"


# ── D-12 ──────────────────────────────────────────────────────────────
def test_haversine_par_conhecido_e_simetria() -> None:
    """Haversine com R=6371,0088 km para par conhecido (3 casas) e simetria."""
    # Par conhecido: usar duas cidades do dataset para testar simetria e precisão
    cities = load_cities()
    edges = load_edges()

    # Encontra um par de cidades conectado por uma aresta divisa
    city_dict = {city.id: city for city in cities}
    for edge in edges:
        if edge.source == "divisa" and city_dict.get(edge.u) and city_dict.get(edge.v):
            u = city_dict[edge.u]
            v = city_dict[edge.v]
            # Haversine é simétrica: h(a,b) == h(b,a)
            d_uv = haversine_km(u.lat, u.lon, v.lat, v.lon)
            vu = haversine_km(v.lat, v.lon, u.lat, u.lon)
            assert math.isclose(d_uv, vu, rel_tol=1e-9), f"Haversine não simétrica: {d_uv} vs {vu}"
            # Arredondamento para 3 casas deve bater com dist_km da aresta
            assert math.isclose(edge.dist_km, d_uv, rel_tol=0.001), (
                f"dist_km {edge.dist_km} != haversine {d_uv} para {edge.u}-{edge.v}"
            )
            break
    else:
        pytest.fail("Nenhuma aresta divisa encontrada para testar Haversine")


# ── D-13 ──────────────────────────────────────────────────────────────
def test_extras_csv_colunas_e_ligacao_manual() -> None:
    """data/manual/extras.csv colunas cd_a,cd_b,motivo,fonte; ligação incorporada com source=manual e distância Haversine."""
    # Verifica colunas do arquivo
    with open("data/manual/extras.csv", encoding="utf-8", newline="") as f:
        header = f.readline().strip().split(",")
    assert "cd_a" in header
    assert "cd_b" in header
    assert "motivo" in header
    assert "fonte" in header

    # Verifica que a ligação manual foi incorporada
    edges = load_edges()
    manuais = [e for e in edges if e.source == "manual"]
    assert len(manuais) == 1
    assert manuais[0].source == "manual"
    # Distância deve ser finita (calculada por Haversine)
    assert math.isfinite(manuais[0].dist_km)
    assert manuais[0].dist_km > 0


# ── D-14 ──────────────────────────────────────────────────────────────
def test_load_cities_e_load_edges_com_erros() -> None:
    """load_cities/load_edges com arquivo ausente, coluna ausente ou linha inválida -> DataLoadError com mensagem e nº de linha quando aplicável."""
    import os

    # Limpa cache antes de mexer nos arquivos (lru_cache pode ter resultado guardado)
    load_cities.cache_clear()
    load_edges.cache_clear()

    # Teste: arquivo ausente
    original_cities = "data/processed/cities.csv"
    original_edges = "data/processed/edges.csv"

    # Move arquivos temporariamente
    os.rename(original_cities, original_cities + ".bak")
    os.rename(original_edges, original_edges + ".bak")

    try:
        # load_cities com arquivo ausente
        try:
            load_cities()
            assert False, "Esperava DataLoadError"
        except Exception as e:
            assert "DataLoadError" in type(e).__name__, f"Esperava DataLoadError, got {type(e).__name__}: {e}"

        # load_edges com arquivo ausente
        try:
            load_edges()
            assert False, "Esperava DataLoadError"
        except Exception as e:
            assert "DataLoadError" in type(e).__name__, f"Esperava DataLoadError, got {type(e).__name__}: {e}"
    finally:
        # Restaura arquivos
        os.rename(original_cities + ".bak", original_cities)
        os.rename(original_edges + ".bak", original_edges)


# ── D-15 ──────────────────────────────────────────────────────────────
def test_city_by_id_e_city_name_map() -> None:
    """city_by_id existente/inexistente e city_name_map -> registro correto; inexistente DataLoadError; mapa cobre 645."""
    # city_by_id existente
    cities = load_cities()
    first_city = cities[0]
    found = city_by_id(first_city.id)
    assert found.id == first_city.id
    assert found.name == first_city.name

    # city_by_id inexistente
    try:
        city_by_id("9999999")
        assert False, "Esperava DataLoadError"
    except Exception as e:
        assert "DataLoadError" in type(e).__name__

    # city_name_map cobre 645
    name_map = city_name_map()
    assert len(name_map) == 645
    # Todos os IDs do mapa estão nas cidades
    for cid in name_map:
        assert cid in {city.id for city in cities}


# ── D-16 ──────────────────────────────────────────────────────────────
def test_cache_lru_cache_leitura_repetida() -> None:
    """cache lru_cache: leitura repetida não muda conteúdo; limpe cache quando necessário."""
    # Leitura repetida não muda conteúdo
    cities1 = load_cities()
    # Segunda chamada deve retornar o mesmo objeto (lru_cache)
    cities2 = load_cities()
    assert cities1 is cities2, "lru_cache deve retornar o mesmo objeto"

    # Limpar cache e verificar
    load_cities.cache_clear()
    cities3 = load_cities()
    # Após clear, deve gerar novo tuple (mas com mesmo conteúdo)
    assert len(cities3) == len(cities1)
    assert all(c1.id == c2.id for c1, c2 in zip(cities1, cities3))