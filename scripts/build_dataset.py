"""Prepara os dados do projeto a partir dos arquivos brutos do IBGE.

Execução (uma vez, ou sempre que os dados brutos mudarem):

    python scripts/build_dataset.py

O script lê ``data/raw/``, valida os fatos conhecidos da malha municipal de
São Paulo e grava os arquivos usados pelo sistema em ``data/processed/``.
Ele NÃO faz parte da aplicação em execução: o sistema lê apenas os arquivos
processados.

Fontes:
- IBGE, Municípios Limítrofes 2024 (aba "Municípios Limítrofes").
- kelvins/municipios-brasileiros (coordenadas das sedes, licença MIT).
"""

from __future__ import annotations

import csv
import logging
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from odf import teletype
from odf.opendocument import load
from odf.table import Table, TableCell, TableRow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Caminhos e constantes
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MANUAL_DIR = PROJECT_ROOT / "data" / "manual"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ODS_FILE = RAW_DIR / "BR_Municipios_2024_LIMITROFES.ods"
CITIES_FILE = RAW_DIR / "municipios.csv"
EXTRAS_FILE = MANUAL_DIR / "extras.csv"

SHEET_NAME = "Municípios Limítrofes"
SP_STATE_CODE = "35"
EARTH_RADIUS_KM = 6371.0088

# Fatos verificados nos arquivos reais (ver .sdd/PLAN.md, seção 4.2).
EXPECTED_SP_CITIES = 645
EXPECTED_SP_SP_EDGES = 1832
EXPECTED_SP_ORIGIN_ROWS = 3864
EXPECTED_SP_SP_ORDERED_ROWS = 3664
EXPECTED_SP_OTHER_STATE_ROWS = 199
EXPECTED_UNIQUE_ZERO_BORDER = 54
EXPECTED_UNIQUE_SHORT_BORDER = 71
EXPECTED_NAME_DIVERGENCES = {
    "3506607",  # Biritiba Mirim (ODS) x Biritiba-Mirim (CSV)
    "3516101",  # Florínea (ODS) x Florínia (CSV)
    "3522158",  # Itaoca (ODS) x Itaóca (CSV)
}
ILHABELA_CODE = "3520400"

EDGE_FIELDS = ["u", "v", "dist_km", "border_km", "source", "short_border"]


class DatasetError(RuntimeError):
    """Erro de validação dos dados: interrompe a geração com mensagem clara."""


@dataclass
class City:
    id: str
    name: str
    lat: float
    lon: float


@dataclass
class EdgeRecord:
    u: str
    v: str
    dist_km: float
    border_km: float | None
    source: str
    short_border: bool


# ---------------------------------------------------------------------------
# Leitura dos arquivos brutos
# ---------------------------------------------------------------------------


def _extract_cell_text(cell: TableCell) -> str:
    """Extrai o texto visível de uma célula do ODS."""
    return teletype.extractText(cell).strip()


def read_ods_rows(path: Path) -> list[list[str]]:
    """Lê a aba de municípios limítrofes e devolve as linhas como listas.

    O ODS pode usar células repetidas (``number-columns-repeated``); elas são
    expandidas para manter o alinhamento das colunas.
    """
    if not path.exists():
        raise DatasetError(f"Arquivo não encontrado: {path}")

    document = load(str(path))
    tables = document.getElementsByType(Table)
    target = next(
        (table for table in tables if table.getAttribute("name") == SHEET_NAME),
        None,
    )
    if target is None:
        names = [table.getAttribute("name") for table in tables]
        raise DatasetError(
            f"A aba '{SHEET_NAME}' não foi encontrada no ODS. Abas lidas: {names}"
        )

    rows: list[list[str]] = []
    for row in target.getElementsByType(TableRow):
        values: list[str] = []
        for cell in row.getElementsByType(TableCell):
            repeat = int(
                cell.attributes.get(
                    ("urn:oasis:names:tc:opendocument:xmlns:table:1.0", "number-columns-repeated"),
                    "1",
                )
            )
            values.extend([_extract_cell_text(cell)] * repeat)
        rows.append(values)
    return rows


def read_cities_csv(path: Path) -> dict[str, City]:
    """Lê as coordenadas das sedes municipais e filtra São Paulo (UF 35)."""
    if not path.exists():
        raise DatasetError(f"Arquivo não encontrado: {path}")

    cities: dict[str, City] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"codigo_ibge", "nome", "latitude", "longitude", "codigo_uf"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise DatasetError(f"Colunas ausentes em {path.name}: {sorted(missing)}")

        for line_number, row in enumerate(reader, start=2):
            if row["codigo_uf"] != SP_STATE_CODE:
                continue
            city_id = row["codigo_ibge"].strip()
            if len(city_id) != 7 or not city_id.isdigit():
                raise DatasetError(
                    f"Código IBGE inválido em {path.name}, linha {line_number}: {city_id!r}"
                )
            if city_id in cities:
                raise DatasetError(f"Código IBGE duplicado em {path.name}: {city_id}")
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (TypeError, ValueError) as exc:
                raise DatasetError(
                    f"Coordenada inválida em {path.name}, linha {line_number}: "
                    f"{row['latitude']!r}, {row['longitude']!r}"
                ) from exc
            if not (math.isfinite(lat) and math.isfinite(lon)):
                raise DatasetError(
                    f"Coordenada não finita em {path.name}, linha {line_number}: {city_id}"
                )
            cities[city_id] = City(
                id=city_id,
                name=row["nome"].strip(),
                lat=lat,
                lon=lon,
            )
    return cities


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    """Distância em km entre dois pontos pela fórmula de Haversine."""
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    delta_phi = phi_b - phi_a
    delta_lambda = math.radians(lon_b - lon_a)
    h = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


# ---------------------------------------------------------------------------
# Construção das arestas
# ---------------------------------------------------------------------------


def parse_border_km(raw: str, context: str) -> float | None:
    """Converte a extensão da divisa (vírgula decimal) para float."""
    if raw == "":
        return None
    try:
        value = float(raw.replace(",", "."))
    except ValueError as exc:
        raise DatasetError(f"COMP_KM inválido ({raw!r}) em {context}") from exc
    if not math.isfinite(value) or value < 0:
        raise DatasetError(f"COMP_KM fora do esperado ({raw!r}) em {context}")
    return value


def build_divisa_edges(
    rows: list[list[str]], cities: dict[str, City]
) -> tuple[list[EdgeRecord], dict[str, int], dict[str, str]]:
    """Monta as arestas SP-SP a partir da planilha do IBGE.

    Retorna as arestas, contadores de validação e os nomes exibidos (grafia do
    IBGE), sempre juntando por código IBGE.
    """
    header = [value.strip() for value in rows[0]]
    expected_header = ["CD_MUN", "NM_MUN", "N_LIM", "CD_LIM", "NM_LIM", "COMP_KM"]
    if header[:6] != expected_header:
        raise DatasetError(f"Cabeçalho inesperado no ODS: {header[:6]}")

    stats = {
        "sp_origin_rows": 0,
        "sp_sp_ordered_rows": 0,
        "sp_other_state_rows": 0,
        "sp_empty_rows": 0,
    }
    display_names: dict[str, str] = {}
    directed: dict[tuple[str, str], float | None] = {}

    for offset, row in enumerate(rows[1:], start=2):
        padded = row + [""] * (6 - len(row))
        cd_mun, nm_mun, _n_lim, cd_lim, _nm_lim, comp_km = padded[:6]
        cd_mun = cd_mun.strip()
        cd_lim = cd_lim.strip()
        if not cd_mun.startswith(SP_STATE_CODE):
            continue

        stats["sp_origin_rows"] += 1
        # A grafia oficial exibida é a da planilha do IBGE.
        previous = display_names.setdefault(cd_mun, nm_mun.strip())
        if previous != nm_mun.strip():
            raise DatasetError(
                f"Nome divergente para o código {cd_mun} dentro do próprio ODS: "
                f"{previous!r} x {nm_mun.strip()!r}"
            )

        if not cd_lim:
            stats["sp_empty_rows"] += 1
            continue
        if not cd_lim.startswith(SP_STATE_CODE):
            stats["sp_other_state_rows"] += 1
            continue
        if cd_mun == cd_lim:
            raise DatasetError(f"Laço inesperado no ODS na linha {offset}: {cd_mun}")

        stats["sp_sp_ordered_rows"] += 1
        border = parse_border_km(comp_km.strip(), f"linha {offset}")
        directed[(cd_mun, cd_lim)] = border

    # Valida simetria: cada relação SP-SP deve aparecer nos dois sentidos.
    asymmetric = [pair for pair in directed if (pair[1], pair[0]) not in directed]
    if asymmetric:
        raise DatasetError(
            "Relação de limítrofes assimétrica. Exemplos: "
            + ", ".join(f"{u}->{v}" for u, v in asymmetric[:5])
        )

    edges: list[EdgeRecord] = []
    for (u, v), border in directed.items():
        if u > v:
            continue  # cada par não ordenado é processado uma única vez
        reverse_border = directed[(v, u)]
        if border != reverse_border:
            raise DatasetError(
                f"COMP_KM divergente entre os dois sentidos de {u}-{v}: "
                f"{border!r} x {reverse_border!r}"
            )
        if u not in cities or v not in cities:
            missing = [code for code in (u, v) if code not in cities]
            raise DatasetError(
                f"Município do ODS sem coordenada no CSV: {missing}"
            )
        distance = round(
            haversine_km(
                cities[u].lat,
                cities[u].lon,
                cities[v].lat,
                cities[v].lon,
            ),
            3,
        )
        if not math.isfinite(distance):
            raise DatasetError(f"Distância inválida calculada para {u}-{v}")
        edges.append(
            EdgeRecord(
                u=u,
                v=v,
                dist_km=distance,
                border_km=border,
                source="divisa",
                short_border=border is not None and border < 0.5,
            )
        )

    edges.sort(key=lambda edge: (edge.u, edge.v))
    return edges, stats, display_names


def read_manual_edges(
    path: Path, cities: dict[str, City], existing_pairs: set[tuple[str, str]]
) -> list[EdgeRecord]:
    """Lê as ligações manuais documentadas em ``data/manual/extras.csv``."""
    if not path.exists():
        raise DatasetError(f"Arquivo de ligações manuais não encontrado: {path}")

    edges: list[EdgeRecord] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"cd_a", "cd_b", "motivo", "fonte"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise DatasetError(f"Colunas ausentes em {path.name}: {sorted(missing)}")

        for line_number, row in enumerate(reader, start=2):
            u = row["cd_a"].strip()
            v = row["cd_b"].strip()
            if u == v:
                raise DatasetError(f"Laço em {path.name}, linha {line_number}: {u}")
            if u not in cities or v not in cities:
                missing_codes = [code for code in (u, v) if code not in cities]
                raise DatasetError(
                    f"Código inexistente em {path.name}, linha {line_number}: {missing_codes}"
                )
            if not row["motivo"].strip() or not row["fonte"].strip():
                raise DatasetError(
                    f"Motivo/fonte vazios em {path.name}, linha {line_number}"
                )
            pair = (min(u, v), max(u, v))
            if pair in existing_pairs:
                raise DatasetError(
                    f"Ligação manual duplicada de uma divisa em {path.name}: {pair}"
                )
            existing_pairs.add(pair)
            distance = round(
                haversine_km(
                    cities[u].lat,
                    cities[u].lon,
                    cities[v].lat,
                    cities[v].lon,
                ),
                3,
            )
            edges.append(
                EdgeRecord(
                    u=pair[0],
                    v=pair[1],
                    dist_km=distance,
                    border_km=None,
                    source="manual",
                    short_border=False,
                )
            )
    return edges


# ---------------------------------------------------------------------------
# Validações
# ---------------------------------------------------------------------------


def _components(
    city_ids: set[str], edges: list[EdgeRecord]
) -> list[set[str]]:
    """Componentes conexos por busca em largura (para validar os dados)."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    for city in city_ids:
        adjacency[city]
    for edge in edges:
        adjacency[edge.u].add(edge.v)
        adjacency[edge.v].add(edge.u)

    remaining = set(city_ids)
    components: list[set[str]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        remaining.remove(start)
        component = {start}
        while stack:
            current = stack.pop()
            for neighbour in adjacency[current]:
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    component.add(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def validate_dataset(
    cities: dict[str, City],
    divisa_edges: list[EdgeRecord],
    manual_edges: list[EdgeRecord],
    stats: dict[str, int],
    display_names: dict[str, str],
) -> None:
    """Confere os fatos conhecidos; falha com mensagem clara em divergência."""
    problems: list[str] = []

    if len(cities) != EXPECTED_SP_CITIES:
        problems.append(
            f"Esperados {EXPECTED_SP_CITIES} municípios de SP, encontrados {len(cities)}."
        )
    if len(divisa_edges) != EXPECTED_SP_SP_EDGES:
        problems.append(
            f"Esperadas {EXPECTED_SP_SP_EDGES} arestas de divisa, "
            f"encontradas {len(divisa_edges)}."
        )
    if stats["sp_origin_rows"] != EXPECTED_SP_ORIGIN_ROWS:
        problems.append(
            f"Esperadas {EXPECTED_SP_ORIGIN_ROWS} linhas com origem em SP, "
            f"encontradas {stats['sp_origin_rows']}."
        )
    if stats["sp_sp_ordered_rows"] != EXPECTED_SP_SP_ORDERED_ROWS:
        problems.append(
            f"Esperadas {EXPECTED_SP_SP_ORDERED_ROWS} linhas SP-SP, "
            f"encontradas {stats['sp_sp_ordered_rows']}."
        )
    if stats["sp_other_state_rows"] != EXPECTED_SP_OTHER_STATE_ROWS:
        problems.append(
            f"Esperadas {EXPECTED_SP_OTHER_STATE_ROWS} linhas de SP com vizinho "
            f"de outro estado, encontradas {stats['sp_other_state_rows']}."
        )

    unique_zero = sum(1 for edge in divisa_edges if edge.border_km == 0)
    if unique_zero != EXPECTED_UNIQUE_ZERO_BORDER:
        problems.append(
            f"Esperadas {EXPECTED_UNIQUE_ZERO_BORDER} arestas com divisa 0 km, "
            f"encontradas {unique_zero}."
        )
    unique_short = sum(1 for edge in divisa_edges if edge.short_border)
    if unique_short != EXPECTED_UNIQUE_SHORT_BORDER:
        problems.append(
            f"Esperadas {EXPECTED_UNIQUE_SHORT_BORDER} arestas com divisa < 0,5 km, "
            f"encontradas {unique_short}."
        )

    # Só Ilhabela pode ficar isolada antes das ligações manuais.
    divisa_components = _components(set(cities), divisa_edges)
    isolated = sorted(
        component.pop() for component in divisa_components if len(component) == 1
    )
    if isolated != [ILHABELA_CODE]:
        problems.append(
            f"Esperado apenas Ilhabela ({ILHABELA_CODE}) isolada, encontrados: {isolated}."
        )
    largest = max((len(component) for component in divisa_components), default=0)
    if largest != EXPECTED_SP_CITIES - 1:
        problems.append(
            f"Esperado um componente de {EXPECTED_SP_CITIES - 1} municípios, "
            f"encontrado {largest}."
        )

    csv_names = {city.id: city.name for city in cities.values()}
    divergences = {
        city_id
        for city_id, ods_name in display_names.items()
        if city_id in csv_names and csv_names[city_id] != ods_name
    }
    if divergences != EXPECTED_NAME_DIVERGENCES:
        problems.append(
            "Divergências de nome entre ODS e CSV diferentes do esperado: "
            f"{sorted(divergences)}."
        )

    # Depois das manuais, Ilhabela deve estar conectada.
    all_components = _components(set(cities), divisa_edges + manual_edges)
    if len(all_components) != 1:
        problems.append(
            f"Com as ligações manuais esperava-se 1 componente, "
            f"encontrados {len(all_components)}."
        )

    if problems:
        message = "Validação dos dados falhou:\n- " + "\n- ".join(problems)
        raise DatasetError(message)


# ---------------------------------------------------------------------------
# Escrita dos arquivos processados
# ---------------------------------------------------------------------------


def write_outputs(
    cities: dict[str, City],
    edges: list[EdgeRecord],
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    cities_path = PROCESSED_DIR / "cities.csv"
    with cities_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "name", "lat", "lon"])
        for city in sorted(cities.values(), key=lambda item: item.id):
            writer.writerow([city.id, city.name, city.lat, city.lon])

    edges_path = PROCESSED_DIR / "edges.csv"
    with edges_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EDGE_FIELDS)
        writer.writeheader()
        for edge in sorted(edges, key=lambda item: (item.u, item.v)):
            writer.writerow(
                {
                    "u": edge.u,
                    "v": edge.v,
                    "dist_km": f"{edge.dist_km:.3f}",
                    "border_km": "" if edge.border_km is None else f"{edge.border_km:.3f}",
                    "source": edge.source,
                    "short_border": "true" if edge.short_border else "false",
                }
            )

    logger.info(
        "  %s: %d municípios", cities_path.relative_to(PROJECT_ROOT), len(cities)
    )
    logger.info("  %s: %d arestas", edges_path.relative_to(PROJECT_ROOT), len(edges))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Lendo dados brutos...")
    rows = read_ods_rows(ODS_FILE)
    cities = read_cities_csv(CITIES_FILE)
    logger.info("  Municípios de SP no CSV: %d", len(cities))

    divisa_edges, stats, display_names = build_divisa_edges(rows, cities)
    logger.info("  Arestas de divisa SP-SP: %d", len(divisa_edges))

    existing_pairs = {(edge.u, edge.v) for edge in divisa_edges}
    manual_edges = read_manual_edges(EXTRAS_FILE, cities, existing_pairs)
    logger.info("  Ligações manuais: %d", len(manual_edges))

    logger.info("Validando fatos conhecidos...")
    validate_dataset(cities, divisa_edges, manual_edges, stats, display_names)

    # A grafia exibida é a do IBGE (ODS), conforme decisão documentada.
    for city_id, ods_name in display_names.items():
        cities[city_id].name = ods_name

    logger.info("Gravando dados processados...")
    write_outputs(cities, divisa_edges + manual_edges)
    logger.info("Concluído.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DatasetError as error:
        logger.error("ERRO: %s", error)
        sys.exit(1)
