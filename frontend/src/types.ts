export interface City {
  id: string
  name: string
  lat: number
  lon: number
  neighbors: string[]
}

export interface PresetSummary {
  id: string
  name: string
  description: string
  n_nodes: number
  n_edges: number
  n_components: number
  include_manual: boolean
}

export interface GraphNode {
  id: string
  name?: string | null
  lat?: number | null
  lon?: number | null
}

export interface EdgeAttrs {
  border_km?: number | null
  source?: string
  short_border?: boolean
  [key: string]: unknown
}

export interface Edge {
  u: string
  v: string
  weight: number
  attrs: EdgeAttrs
}

export interface DiscardedCity {
  id: string
  name: string
  reason: string
}

export interface GraphStats {
  n_nodes: number
  n_edges: number
  n_components: number
  is_connected: boolean
  n_divisa_edges: number
  n_manual_edges: number
  component_sizes: number[]
}

export interface GraphData {
  nodes: GraphNode[]
  edges: Edge[]
  warnings: string[]
  discarded: DiscardedCity[]
  stats?: GraphStats | null
}

export interface PresetDetail {
  id: string
  name: string
  description: string
  include_manual: boolean
  graph: GraphData
}

export interface ResultComponent {
  size: number
  node_ids: string[]
}

export interface TraceEvent {
  type: 'consider' | 'accept' | 'reject' | 'start' | 'restart' | 'push' | 'pop' | 'skip'
  step?: number
  edge?: Edge
  edges?: { u: string; v: string; weight: number }[]
  vertex?: string
  from_vertex?: string
  new_vertex?: string
  component_index?: number
  component_u_size?: number
  component_v_size?: number
  same_component?: boolean
  total_cost_so_far?: number
  accepted_count?: number
  tree_size?: number
  cut_size?: number
  heap_size?: number
  reason?: string
}

export interface MstResult {
  algorithm: 'kruskal' | 'prim'
  edges: Edge[]
  total_cost: number
  n_components: number
  components: ResultComponent[]
  is_forest: boolean
  metrics: Record<string, number>
  trace: TraceEvent[] | null
}

export interface Comparison {
  same_cost: boolean | null
  same_edges: boolean | null
  cost_difference: number | null
  has_weight_ties: boolean | null
  kruskal_only_edges: Edge[]
  prim_only_edges: Edge[]
  is_consistent: boolean | null
  message: string
}

export interface Verification {
  performed: boolean
  is_forest: boolean
  cycle_property: boolean
  is_valid: boolean
  cost_consistent: boolean
  message: string
  details: string[]
}

export interface RunResponse {
  kruskal: MstResult | null
  prim: MstResult | null
  comparison: Comparison
  verification: Record<string, Verification> | null
  graph_stats: GraphStats
  warnings: string[]
}

export interface BenchmarkRow {
  n_nodes: number
  n_edges: number
  kruskal_ms: number
  kruskal_p25_ms: number
  kruskal_p75_ms: number
  prim_ms: number
  prim_p25_ms: number
  prim_p75_ms: number
}

export interface BenchmarkResponse {
  rows: BenchmarkRow[]
  meta: {
    preset_id: string
    preset_name: string
    start_city: string
    start_city_name: string
    runs: number
    note: string
  }
}

export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    details: unknown[]
  }
}
