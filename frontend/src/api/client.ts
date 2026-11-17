import type {
  ApiErrorPayload,
  BenchmarkResponse,
  City,
  GraphData,
  PresetDetail,
  PresetSummary,
  RunResponse,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: string[]

  constructor(message: string, status: number, code: string, details: string[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(
      'Não foi possível falar com o servidor. Verifique se o backend está rodando.',
      0,
      'NETWORK_ERROR'
    )
  }

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null
    try {
      payload = (await response.json()) as ApiErrorPayload
    } catch {
      // Resposta sem JSON: mantém a mensagem genérica.
    }
    const error = payload?.error
    const details = Array.isArray(error?.details) ? error.details.map((item) => String(item)) : []
    throw new ApiError(
      error?.message ?? `A requisição falhou (HTTP ${response.status}).`,
      response.status,
      error?.code ?? 'HTTP_ERROR',
      details
    )
  }

  return (await response.json()) as T
}

export const api = {
  async cities(): Promise<City[]> {
    const data = await request<{ cities: City[] }>('/api/v1/cities')
    return data.cities
  },

  async presets(): Promise<PresetSummary[]> {
    const data = await request<{ presets: PresetSummary[] }>('/api/v1/presets')
    return data.presets
  },

  async preset(id: string): Promise<PresetDetail> {
    return request<PresetDetail>(`/api/v1/presets/${encodeURIComponent(id)}`)
  },

  async buildGraph(
    cityIds: string[],
    includeManual: boolean,
    connectComponents = false
  ): Promise<GraphData> {
    return request<GraphData>('/api/v1/graph/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        city_ids: cityIds,
        include_manual: includeManual,
        connect_components: connectComponents,
      }),
    })
  },

  async uploadGraph(file: File): Promise<GraphData> {
    const form = new FormData()
    form.append('file', file)
    const data = await request<{ graph: GraphData }>('/api/v1/graph/upload', {
      method: 'POST',
      body: form,
    })
    return data.graph
  },

  async run(payload: {
    graph: GraphData
    algorithm: 'kruskal' | 'prim' | 'both'
    start_vertex: string | null
    trace: boolean
    verify: boolean
  }): Promise<RunResponse> {
    return request<RunResponse>('/api/v1/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },

  async benchmark(payload: {
    graph?: GraphData | null
    preset_id?: string | null
    runs: number
    start_city_name?: string | null
  }): Promise<BenchmarkResponse> {
    return request<BenchmarkResponse>('/api/v1/benchmark', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
}
