"""Rotas HTTP da API. Apenas traduzem HTTP para os serviços de domínio."""

from __future__ import annotations

import unicodedata

from fastapi import APIRouter, File, Query, UploadFile

from ..algorithms.graph import Graph, GraphValidationError
from ..errors import PayloadTooLargeError, ValidationError
from ..services.benchmark import run_benchmark
from ..services.graph_selection import build_from_city_ids, city_catalog
from ..services.presets import get_preset, get_presets
from ..services.run_service import run_algorithms
from ..services.serialization import graph_to_dict
from ..services.uploads import MAX_EDGES, MAX_UPLOAD_BYTES, parse_upload
from .schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    BuildGraphRequest,
    CitiesResponse,
    GraphDTO,
    PresetDetailDTO,
    PresetsResponse,
    RunRequest,
    RunResponse,
    UploadResponseDTO,
)

router = APIRouter(prefix="/api/v1", tags=["árvore geradora mínima"])

MAX_TRACE_EDGES = 20_000
MAX_GRAPH_NODES = 200_000

# Campos aceitos pelo parâmetro ``sort`` de ``GET /api/cities``.
CITY_SORT_FIELDS = ("name", "id", "lat", "lon")


def _fold(text: str) -> str:
    """Normaliza texto para comparação: minúsculas e sem acentos.

    Assim ``q=sao`` encontra ``São Paulo`` e ``q=bauru`` encontra ``Bauru``.
    """
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _graph_from_dto(payload: GraphDTO) -> Graph:
    """Converte o grafo enviado pelo frontend em ``Graph`` validado."""
    if len(payload.edges) > MAX_EDGES:
        raise PayloadTooLargeError(
            f"O grafo tem {len(payload.edges)} arestas; o limite é {MAX_EDGES}."
        )
    if len(payload.nodes) > MAX_GRAPH_NODES:
        raise PayloadTooLargeError(
            f"O grafo tem {len(payload.nodes)} vértices; o limite é {MAX_GRAPH_NODES}."
        )
    try:
        return Graph.from_records(
            [node.model_dump() for node in payload.nodes],
            [edge.model_dump() for edge in payload.edges],
        )
    except GraphValidationError as error:
        raise ValidationError(str(error)) from error


@router.get("/cities", response_model=CitiesResponse)
def list_cities(
    q: str | None = Query(
        default=None,
        description=(
            "Filtro pelo nome do município, sem diferenciar maiúsculas nem "
            "acentos (ex.: 'sao' encontra 'São Paulo')."
        ),
    ),
    limit: int | None = Query(
        default=None,
        ge=1,
        description=(
            "Máximo de itens da página. Omitido devolve a lista completa "
            "(comportamento antigo, usado pelo frontend)."
        ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Itens ignorados depois do filtro, antes do recorte da página.",
    ),
    sort: str = Query(
        default="name",
        description=(
            "Campo de ordenação: name, id, lat ou lon. Um '-' na frente "
            "inverte a ordem (ex.: -name)."
        ),
    ),
) -> dict[str, object]:
    """Lista paginada de municípios, com filtro por nome e ordenação.

    Retorna o envelope ``{items, total, limit, offset}`` do PLAN §9, mais a
    chave ``cities`` (alias de ``items``) mantida por retrocompatibilidade
    com o frontend e com os testes atuais. Sem parâmetros a resposta é a
    lista completa, como antes.
    """
    field = sort[1:] if sort.startswith("-") else sort
    if field not in CITY_SORT_FIELDS:
        raise ValidationError(
            f"Ordenação inválida: '{sort}'. Use um destes campos: "
            f"{', '.join(CITY_SORT_FIELDS)} (prefixe com '-' para ordem "
            "decrescente)."
        )

    catalog = list(city_catalog())
    if q and q.strip():
        needle = _fold(q.strip())
        matched = [
            city for city in catalog if needle in _fold(str(city["name"]))
        ]
    else:
        matched = catalog

    reverse = sort.startswith("-")
    if field == "name":
        # Padrão do catálogo: ordem alfabética por nome (sem acento na chave
        # de comparação), estável entre requisições.
        matched.sort(
            key=lambda city: str(city["name"]).casefold(), reverse=reverse
        )
    else:
        matched.sort(
            key=lambda city: (city[field], str(city["id"])), reverse=reverse
        )

    total = len(matched)
    end = None if limit is None else offset + limit
    page = matched[offset:end]

    return {
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "cities": page,
    }


@router.get("/presets", response_model=PresetsResponse)
def list_presets() -> dict[str, object]:
    """Resumo das instâncias prontas."""
    return {"presets": [preset.summary() for preset in get_presets()]}


@router.get("/presets/{preset_id}", response_model=PresetDetailDTO)
def preset_detail(preset_id: str) -> dict[str, object]:
    """Grafo completo de uma instância pronta."""
    preset = get_preset(preset_id)
    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "include_manual": preset.include_manual,
        "graph": graph_to_dict(
            preset.graph,
            warnings=preset.warnings,
            discarded=preset.discarded,
        ),
    }


@router.post("/graph/build", response_model=GraphDTO)
def build_graph(request: BuildGraphRequest) -> dict[str, object]:
    """Monta o subgrafo induzido pela seleção de municípios."""
    built = build_from_city_ids(
        request.city_ids,
        include_manual=request.include_manual,
        connect_components=request.connect_components,
    )
    return graph_to_dict(
        built.graph,
        warnings=built.warnings,
        discarded=built.discarded,
    )


@router.post("/graph/upload", response_model=UploadResponseDTO)
async def upload_graph(file: UploadFile = File(...)) -> dict[str, object]:
    """Recebe CSV ou JSON, valida e devolve o grafo (ou erro legível)."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    parsed = parse_upload(file.filename or "grafo", content)
    return {
        "graph": graph_to_dict(
            parsed.graph,
            warnings=parsed.warnings,
            discarded=parsed.discarded,
        )
    }


@router.post("/run", response_model=RunResponse)
def run(request: RunRequest) -> dict[str, object]:
    """Executa Kruskal, Prim ou ambos, com trace e verificação opcionais."""
    if request.preset_id is not None:
        graph = get_preset(request.preset_id).graph
    else:
        assert request.graph is not None  # garantido pelo validador do schema
        graph = _graph_from_dto(request.graph)

    if request.trace and graph.n_edges > MAX_TRACE_EDGES:
        raise ValidationError(
            f"O modo passo a passo está disponível para grafos com até "
            f"{MAX_TRACE_EDGES} arestas; este grafo tem {graph.n_edges}. "
            "Execute sem trace para obter o resultado."
        )

    return run_algorithms(
        graph,
        algorithm=request.algorithm,
        start_vertex=request.start_vertex,
        trace=request.trace,
        verify=request.verify,
    )


@router.post("/benchmark", response_model=BenchmarkResponse)
def benchmark(request: BenchmarkRequest) -> dict[str, object]:
    """Executa a análise de tempo por tamanho de instância.

    Aceita um grafo enviado pelo usuário (mesmo padrão do endpoint ``/run``)
    ou, alternativamente, um preset_id para o comportamento histórico baseado
    em subgrafos por BFS a partir de Bauru.
    """
    graph = None
    if request.graph is not None:
        graph = _graph_from_dto(request.graph)

    return run_benchmark(
        graph=graph,
        preset_id=request.preset_id or "p3-estado-sp",
        runs=request.runs,
        start_city_name=request.start_city_name or "Bauru",
    )
