"""Testes do leitor de uploads CSV/JSON e dos arquivos de exemplo."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.algorithms.kruskal import kruskal
from backend.app.errors import PayloadTooLargeError, ValidationError
from backend.app.services.uploads import MAX_UPLOAD_BYTES, parse_upload

RAIZ = Path(__file__).resolve().parents[1]
EXAMPLES = RAIZ / "examples"


def _upload(name: str, text: str):
    return parse_upload(name, text.encode("utf-8"))


def test_csv_valido_calcula_mst_classica() -> None:
    parsed = _upload(
        "grafo.csv",
        "origem,destino,peso\n"
        "A,B,4\nA,C,2\nB,C,1\nB,D,5\nC,D,8\nC,E,10\nD,E,2\nD,F,6\nE,F,3\n",
    )

    assert parsed.graph.n_nodes == 6
    assert parsed.graph.n_edges == 9
    assert kruskal(parsed.graph).total_cost == pytest.approx(13.0)
    assert parsed.warnings == []


def test_csv_aceita_ponto_e_virgula_e_virgula_decimal() -> None:
    parsed = _upload(
        "grafo.csv",
        "origem;destino;peso\nA;B;1,5\nB;C;2,5\nA;C;10\n",
    )

    assert parsed.graph.n_edges == 3
    assert kruskal(parsed.graph).total_cost == pytest.approx(4.0)


def test_csv_aceita_cabecalho_em_ingles_e_bom() -> None:
    parsed = parse_upload(
        "grafo.csv",
        "\ufeffsource,target,weight\nA,B,3\nB,C,4\n".encode("utf-8"),
    )

    assert parsed.graph.n_nodes == 3
    assert kruskal(parsed.graph).total_cost == pytest.approx(7.0)


def test_csv_com_laco_e_duplicata_gera_avisos_e_mantem_menor_peso() -> None:
    parsed = _upload(
        "grafo.csv",
        "origem,destino,peso\nA,B,2\nB,A,5\nA,A,1\nB,C,3\n",
    )

    assert parsed.graph.n_edges == 2
    edge_ab = next(
        edge for edge in parsed.graph.edges if {edge.u, edge.v} == {"A", "B"}
    )
    assert edge_ab.weight == pytest.approx(2.0)
    assert any("Laço" in warning for warning in parsed.warnings)
    assert any("duplicada" in warning for warning in parsed.warnings)


def test_csv_com_peso_negativo_gera_aviso_e_mst_negativa() -> None:
    parsed = _upload(
        "grafo.csv",
        "origem,destino,peso\nA,B,-5\nB,C,-2\nC,D,-1\nA,D,10\nB,D,3\n",
    )

    assert any("negativo" in warning for warning in parsed.warnings)
    assert kruskal(parsed.graph).total_cost == pytest.approx(-8.0)


def test_csv_com_peso_invalido_aponta_a_linha() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _upload("grafo.csv", "origem,destino,peso\nA,B,abc\nB,C,3\n")

    assert "linha 2" in str(excinfo.value).lower() or any(
        "linha 2" in detail.lower() for detail in excinfo.value.details
    )


def test_csv_sem_coluna_de_peso_gera_erro_legivel() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _upload("grafo.csv", "origem,destino\nA,B\n")

    assert "peso" in str(excinfo.value).lower()


def test_csv_sem_linhas_de_dados_gera_erro() -> None:
    with pytest.raises(ValidationError, match="nenhuma aresta"):
        _upload("grafo.csv", "origem,destino,peso\n")


def test_json_valido_preserva_nomes_e_coordenadas() -> None:
    parsed = _upload(
        "grafo.json",
        """
        {
          "nodes": [
            {"id": "A", "name": "Alfa", "lat": -22.1, "lon": -49.1},
            {"id": "B", "name": "Beta", "lat": -22.2, "lon": -49.0}
          ],
          "edges": [{"source": "A", "target": "B", "weight": 12.5}]
        }
        """,
    )

    assert parsed.graph.n_nodes == 2
    assert parsed.graph.nodes["A"].name == "Alfa"
    assert parsed.graph.nodes["A"].lat == pytest.approx(-22.1)
    assert kruskal(parsed.graph).total_cost == pytest.approx(12.5)


def test_json_aceita_aliases_u_v_peso() -> None:
    parsed = _upload(
        "grafo.json",
        '{"edges": [{"u": "A", "v": "B", "peso": 4}, {"u": "B", "v": "C", "peso": 2}]}',
    )

    assert parsed.graph.n_nodes == 3
    assert kruskal(parsed.graph).total_cost == pytest.approx(6.0)


def test_json_invalido_aponta_linha() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _upload("grafo.json", '{"edges": [{"source": "A", "target": "B",}]}')

    assert "linha" in str(excinfo.value).lower()


def test_json_com_peso_booleano_gera_erro() -> None:
    with pytest.raises(ValidationError, match="não é um número"):
        _upload(
            "grafo.json",
            '{"nodes": [{"id": "A"}, {"id": "B"}], '
            '"edges": [{"source": "A", "target": "B", "weight": true}]}',
        )


def test_json_com_vertice_duplicado_gera_erro() -> None:
    with pytest.raises(ValidationError, match="duplicado"):
        _upload(
            "grafo.json",
            '{"nodes": [{"id": "A"}, {"id": "A"}], "edges": []}',
        )


def test_arquivo_vazio_gera_erro() -> None:
    with pytest.raises(ValidationError, match="vazio"):
        parse_upload("grafo.csv", b"   \n")


def test_arquivo_acima_do_limite_gera_413() -> None:
    with pytest.raises(PayloadTooLargeError):
        parse_upload("grafo.csv", b"x" * (MAX_UPLOAD_BYTES + 1))


def test_arquivo_sem_utf8_gera_erro_legivel() -> None:
    with pytest.raises(ValidationError, match="UTF-8"):
        parse_upload("grafo.csv", b"\xff\xfeA,B,1\n")


@pytest.mark.parametrize(
    ("filename", "cost"),
    [
        ("grafo_valido.csv", 13.0),
        ("grafo_valido.json", 86.8),
        ("grafo_desconexo.csv", 3.0),
        ("grafo_com_avisos.csv", 5.0),
        ("grafo_pesos_negativos.csv", -8.0),
    ],
)
def test_exemplos_validos_sao_aceitos(filename: str, cost: float) -> None:
    parsed = parse_upload(filename, (EXAMPLES / filename).read_bytes())

    assert kruskal(parsed.graph).total_cost == pytest.approx(cost)


@pytest.mark.parametrize(
    "filename",
    [
        "grafo_peso_invalido.csv",
        "grafo_coluna_ausente.csv",
        "grafo_json_invalido.json",
    ],
)
def test_exemplos_invalidos_geram_erro_legivel(filename: str) -> None:
    with pytest.raises(ValidationError):
        parse_upload(filename, (EXAMPLES / filename).read_bytes())
