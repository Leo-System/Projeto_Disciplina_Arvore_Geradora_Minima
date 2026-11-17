import type {
  BenchmarkResponse,
  BenchmarkRow,
  City,
  Comparison,
  GraphData,
  MstResult,
  RunResponse,
  TraceEvent,
  Verification,
} from '../types'

export const cidades: City[] = [
  {
    id: '3506003',
    name: 'Bauru',
    lat: -22.3145,
    lon: -49.0606,
    neighbors: ['3505500', '3507506'],
  },
  {
    id: '3505500',
    name: 'São Sebastião',
    lat: -23.7601,
    lon: -45.4097,
    neighbors: ['3506003'],
  },
  {
    id: '3507506',
    name: 'Botucatu',
    lat: -22.8858,
    lon: -48.445,
    neighbors: ['3506003'],
  },
]

export const grafo: GraphData = {
  nodes: [
    { id: 'A', name: 'Alfa', lat: -22, lon: -49 },
    { id: 'B', name: 'Beta', lat: -22.2, lon: -49.2 },
    { id: 'C', name: 'Gama', lat: -22.4, lon: -49.4 },
    { id: 'D', name: 'Delta', lat: -22.6, lon: -49.6 },
  ],
  edges: [
    { u: 'A', v: 'B', weight: 1.5, attrs: { source: 'divisa', border_km: 2, short_border: false } },
    {
      u: 'B',
      v: 'C',
      weight: 2.5,
      attrs: { source: 'manual', border_km: null, short_border: false },
    },
    { u: 'C', v: 'D', weight: 0.4, attrs: { source: 'divisa', border_km: 0, short_border: true } },
  ],
  warnings: ['Grafo de teste com aviso.'],
  discarded: [{ id: '9999999', name: 'Ilhabela', reason: 'vértice isolado descartado' }],
  stats: {
    n_nodes: 4,
    n_edges: 3,
    n_components: 1,
    is_connected: true,
    n_divisa_edges: 2,
    n_manual_edges: 1,
    component_sizes: [4],
  },
}

export function criarResultado(
  algorithm: 'kruskal' | 'prim',
  overrides: Partial<MstResult> = {}
): MstResult {
  return {
    algorithm,
    edges: [grafo.edges[0], grafo.edges[1]],
    total_cost: 4,
    n_components: 1,
    components: [{ size: 4, node_ids: ['A', 'B', 'C', 'D'] }],
    is_forest: true,
    metrics:
      algorithm === 'kruskal'
        ? {
            time_ms: 0.25,
            edges_examined: 3,
            accepted: 3,
            rejected: 0,
            find_calls: 6,
            union_calls: 3,
          }
        : {
            time_ms: 1.5,
            edges_examined: 3,
            accepted: 3,
            heap_pushes: 5,
            heap_pops: 4,
            stale_pops: 1,
          },
    trace: [],
    ...overrides,
  }
}

export const verificacao: Verification = {
  performed: true,
  is_forest: true,
  cycle_property: true,
  is_valid: true,
  cost_consistent: true,
  message: 'Resultado válido.',
  details: [],
}

export const comparacao: Comparison = {
  same_cost: true,
  same_edges: true,
  cost_difference: 0,
  has_weight_ties: false,
  kruskal_only_edges: [],
  prim_only_edges: [],
  is_consistent: true,
  message: 'Kruskal e Prim produziram o mesmo custo e o mesmo conjunto de arestas.',
}

export function criarExecucao(overrides: Partial<RunResponse> = {}): RunResponse {
  return {
    kruskal: criarResultado('kruskal'),
    prim: criarResultado('prim'),
    comparison: comparacao,
    verification: { kruskal: verificacao, prim: verificacao },
    graph_stats: grafo.stats!,
    warnings: grafo.warnings,
    ...overrides,
  }
}

export const eventosTrace: TraceEvent[] = [
  {
    type: 'consider',
    edge: grafo.edges[0],
    component_u_size: 1,
    component_v_size: 1,
    same_component: false,
  },
  { type: 'accept', edge: grafo.edges[0], total_cost_so_far: 1.5, accepted_count: 1 },
  {
    type: 'consider',
    edge: grafo.edges[1],
    component_u_size: 2,
    component_v_size: 1,
    same_component: false,
  },
  { type: 'accept', edge: grafo.edges[1], total_cost_so_far: 4, accepted_count: 2 },
]

export const linhasBenchmark: BenchmarkRow[] = [
  { n_nodes: 8, n_edges: 15 },
  { n_nodes: 20, n_edges: 37 },
  { n_nodes: 64, n_edges: 120 },
  { n_nodes: 160, n_edges: 340 },
  { n_nodes: 320, n_edges: 760 },
  { n_nodes: 480, n_edges: 1200 },
  { n_nodes: 644, n_edges: 1832 },
].map(({ n_nodes, n_edges }, indice) => {
  const base = (indice + 1) * 0.9
  return {
    n_nodes,
    n_edges,
    kruskal_ms: base,
    kruskal_p25_ms: base * 0.9,
    kruskal_p75_ms: base * 1.1,
    prim_ms: base * 1.4,
    prim_p25_ms: base * 1.25,
    prim_p75_ms: base * 1.55,
  }
})

export const benchmark: BenchmarkResponse = {
  rows: linhasBenchmark,
  meta: {
    preset_id: 'p3-estado-sp',
    preset_name: 'p3 — Estado de São Paulo (maior componente)',
    start_city: '3506003',
    start_city_name: 'Bauru',
    runs: 20,
    note: 'Tempos dependem da máquina.',
  },
}
