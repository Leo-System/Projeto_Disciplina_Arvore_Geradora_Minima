"""Esquemas Pydantic da API (contrato usado pelo frontend)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Municípios e presets
# ---------------------------------------------------------------------------


class CityDTO(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    neighbors: list[str] = Field(default_factory=list)


class CitiesResponse(BaseModel):
    """Envelope paginado do catálogo de municípios (PLAN §9).

    ``items`` é a página atual (já filtrada por ``q``, ordenada por ``sort``
    e recortada por ``limit``/``offset``); ``total`` conta quantas cidades
    atendem ao filtro, antes da paginação.
    """

    items: list[CityDTO]
    total: int
    limit: int | None = None
    offset: int = 0
    cities: list[CityDTO] = Field(
        default_factory=list,
        description=(
            "Alias retrocompatível, idêntico a ``items``: o frontend e os "
            "testes atuais ainda leem a chave ``cities``."
        ),
    )


class PresetSummaryDTO(BaseModel):
    id: str
    name: str
    description: str
    n_nodes: int
    n_edges: int
    n_components: int
    include_manual: bool


class PresetsResponse(BaseModel):
    presets: list[PresetSummaryDTO]


# ---------------------------------------------------------------------------
# Grafo
# ---------------------------------------------------------------------------


class NodeDTO(BaseModel):
    id: str
    name: str | None = None
    lat: float | None = None
    lon: float | None = None


class EdgeDTO(BaseModel):
    u: str
    v: str
    weight: float
    attrs: dict[str, Any] = Field(default_factory=dict)


class DiscardedDTO(BaseModel):
    id: str
    name: str
    reason: str


class GraphStatsDTO(BaseModel):
    n_nodes: int
    n_edges: int
    n_components: int
    is_connected: bool
    n_divisa_edges: int = 0
    n_manual_edges: int = 0
    component_sizes: list[int] = Field(default_factory=list)


class GraphDTO(BaseModel):
    nodes: list[NodeDTO]
    edges: list[EdgeDTO]
    warnings: list[str] = Field(default_factory=list)
    discarded: list[DiscardedDTO] = Field(default_factory=list)
    stats: GraphStatsDTO | None = None


class PresetDetailDTO(BaseModel):
    id: str
    name: str
    description: str
    include_manual: bool
    graph: GraphDTO


class BuildGraphRequest(BaseModel):
    city_ids: list[str]
    include_manual: bool = True
    connect_components: bool = False


class UploadResponseDTO(BaseModel):
    graph: GraphDTO


# ---------------------------------------------------------------------------
# Execução e comparação
# ---------------------------------------------------------------------------


class ComponentDTO(BaseModel):
    size: int
    node_ids: list[str]


class MSTResultDTO(BaseModel):
    algorithm: str
    edges: list[EdgeDTO]
    total_cost: float
    n_components: int
    components: list[ComponentDTO]
    is_forest: bool
    metrics: dict[str, Any]
    trace: list[dict[str, Any]] | None = None


class ComparisonDTO(BaseModel):
    same_cost: bool | None = None
    same_edges: bool | None = None
    cost_difference: float | None = None
    has_weight_ties: bool | None = None
    kruskal_only_edges: list[EdgeDTO] = Field(default_factory=list)
    prim_only_edges: list[EdgeDTO] = Field(default_factory=list)
    is_consistent: bool | None = None
    message: str


class VerificationDTO(BaseModel):
    performed: bool
    is_forest: bool
    cycle_property: bool
    is_valid: bool
    cost_consistent: bool
    message: str
    details: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    graph: GraphDTO | None = None
    preset_id: str | None = None
    algorithm: Literal["kruskal", "prim", "both"] = "both"
    start_vertex: str | None = None
    trace: bool = False
    verify: bool = True

    @model_validator(mode="after")
    def _exactly_one_graph_source(self) -> "RunRequest":
        if (self.graph is None) == (self.preset_id is None):
            raise ValueError(
                "Informe exatamente um entre 'graph' (grafo montado/enviado) "
                "e 'preset_id' (instância pronta)."
            )
        return self


class RunResponse(BaseModel):
    kruskal: MSTResultDTO | None = None
    prim: MSTResultDTO | None = None
    comparison: ComparisonDTO
    verification: dict[str, VerificationDTO] | None = None
    graph_stats: GraphStatsDTO
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


class BenchmarkRequest(BaseModel):
    graph: GraphDTO | None = None
    preset_id: str | None = "p3-estado-sp"
    runs: int = Field(default=20, ge=1, le=100)
    start_city_name: str | None = None

    @model_validator(mode="after")
    def _exactly_one_graph_source(self) -> "BenchmarkRequest":
        if self.graph is not None:
            # Grafo do usuário prevalece: ignora preset_id mesmo que tenha
            # recebido o valor default.
            self.preset_id = None
        elif self.preset_id is None:
            # Nenhum dos dois informado: usa o preset histórico.
            self.preset_id = "p3-estado-sp"
        return self


class BenchmarkRowDTO(BaseModel):
    n_nodes: int
    n_edges: int
    kruskal_ms: float
    kruskal_p25_ms: float
    kruskal_p75_ms: float
    prim_ms: float
    prim_p25_ms: float
    prim_p75_ms: float


class BenchmarkMetaDTO(BaseModel):
    preset_id: str
    preset_name: str
    start_city: str
    start_city_name: str
    runs: int
    note: str


class BenchmarkResponse(BaseModel):
    rows: list[BenchmarkRowDTO]
    meta: BenchmarkMetaDTO


# ---------------------------------------------------------------------------
# Erros e saúde
# ---------------------------------------------------------------------------


class ErrorDetailDTO(BaseModel):
    code: str
    message: str
    details: list[Any] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetailDTO


class HealthResponse(BaseModel):
    status: str = "ok"
