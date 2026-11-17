import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import type { GraphData, RunResponse } from '../types'
import { ApiError, api } from './client'

const grafo: GraphData = {
  nodes: [{ id: 'A', name: 'Alfa' }],
  edges: [],
  warnings: [],
  discarded: [],
}

const respostaExecucao: RunResponse = {
  kruskal: null,
  prim: null,
  comparison: {
    same_cost: null,
    same_edges: null,
    cost_difference: null,
    has_weight_ties: null,
    kruskal_only_edges: [],
    prim_only_edges: [],
    is_consistent: null,
    message: 'Execute os dois algoritmos.',
  },
  verification: null,
  graph_stats: {
    n_nodes: 1,
    n_edges: 0,
    n_components: 1,
    is_connected: true,
    n_divisa_edges: 0,
    n_manual_edges: 0,
    component_sizes: [1],
  },
  warnings: [],
}

describe('api client', () => {
  it('deve retornar o corpo tipado quando a resposta é 200', async () => {
    // Arrange
    server.use(http.get('*/api/v1/cities', () => HttpResponse.json({ cities: [{ id: '1' }] })))

    // Act
    const cidades = await api.cities()

    // Assert
    expect(cidades).toEqual([{ id: '1' }])
  })

  it('deve lançar ApiError padronizada com status, code, message e details', async () => {
    // Arrange
    server.use(
      http.post('*/api/v1/run', () =>
        HttpResponse.json(
          {
            error: { code: 'VALIDATION_ERROR', message: 'Entrada inválida', details: ['linha 2'] },
          },
          { status: 422 }
        )
      )
    )

    // Act
    const execucao = api.run({
      graph: grafo,
      algorithm: 'both',
      start_vertex: null,
      trace: false,
      verify: true,
    })

    // Assert
    await expect(execucao).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      code: 'VALIDATION_ERROR',
      message: 'Entrada inválida',
      details: ['linha 2'],
    })
  })

  it('deve converter falha de rede em ApiError com status 0 e NETWORK_ERROR', async () => {
    // Arrange
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('falha de rede'))

    // Act
    const chamada = api.cities()

    // Assert
    await expect(chamada).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK_ERROR',
    })
  })

  it('deve usar mensagem genérica com o status quando o erro não tem JSON', async () => {
    // Arrange
    server.use(http.get('*/api/v1/cities', () => new HttpResponse('indisponível', { status: 502 })))

    // Act
    const chamada = api.cities()

    // Assert
    await expect(chamada).rejects.toMatchObject({
      status: 502,
      code: 'HTTP_ERROR',
      message: 'A requisição falhou (HTTP 502).',
      details: [],
    })
  })

  it('deve normalizar details não-array para lista vazia', async () => {
    // Arrange
    server.use(
      http.post('*/api/v1/benchmark', () =>
        HttpResponse.json(
          { error: { code: 'X', message: 'erro', details: 'não é lista' } },
          { status: 500 }
        )
      )
    )

    // Act
    const chamada = api.benchmark(1)

    // Assert
    await expect(chamada).rejects.toMatchObject({ details: [] })
  })

  it('deve codificar o id do preset na URL', async () => {
    // Arrange
    let urlRecebida = ''
    server.use(
      http.get('*/api/v1/presets/*', ({ request }) => {
        urlRecebida = request.url
        return HttpResponse.json({ id: 'p/1', graph: grafo })
      })
    )

    // Act
    await api.preset('p/1')

    // Assert
    expect(urlRecebida).toContain('p%2F1')
  })

  it('deve enviar FormData com o campo file e devolver data.graph', async () => {
    // Arrange: inspeciona o FormData antes da serialização (o parser do MSW
    // perde o nome do arquivo no ambiente jsdom).
    let corpoRecebido: unknown
    const fetchOriginal = globalThis.fetch
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce((_url, init) => {
      corpoRecebido = init?.body
      return Promise.resolve(
        new Response(JSON.stringify({ graph: grafo }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    })

    // Act
    const resultado = await api.uploadGraph(new File(['a,b,c'], 'rede.csv'))

    // Assert
    expect(corpoRecebido).toBeInstanceOf(FormData)
    const dados = corpoRecebido as FormData
    const arquivo = dados.get('file')
    expect(arquivo).toBeInstanceOf(File)
    expect((arquivo as File).name).toBe('rede.csv')
    expect(resultado).toEqual(grafo)

    globalThis.fetch = fetchOriginal
  })

  it('deve enviar todos os campos da execução', async () => {
    // Arrange
    let corpo: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/run', async ({ request }) => {
        corpo = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(respostaExecucao)
      })
    )
    const payload = {
      graph: grafo,
      algorithm: 'prim' as const,
      start_vertex: 'A',
      trace: true,
      verify: false,
    }

    // Act
    const resposta = await api.run(payload)

    // Assert
    expect(corpo).toEqual(payload)
    expect(resposta).toEqual(respostaExecucao)
  })

  it('deve enviar o número de execuções no benchmark (sem grafo → backend usa preset histórico)', async () => {
    // Arrange
    let corpo: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/benchmark', async ({ request }) => {
        corpo = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ rows: [], meta: {} })
      })
    )

    // Act
    await api.benchmark({ runs: 3 })

    // Assert: o frontend envia apenas runs; o backend aplica o preset padrão.
    expect(corpo).toEqual({ runs: 3 })
  })

  it('deve enviar connect_components ao montar o grafo', async () => {
    // Arrange
    let corpo: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/graph/build', async ({ request }) => {
        corpo = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(grafo)
      })
    )

    // Act
    await api.buildGraph(['3506003', '3550704'], true, true)

    // Assert
    expect(corpo).toEqual({
      city_ids: ['3506003', '3550704'],
      include_manual: true,
      connect_components: true,
    })
  })

  it('deve enviar connect_components false por padrão', async () => {
    // Arrange
    let corpo: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/graph/build', async ({ request }) => {
        corpo = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(grafo)
      })
    )

    // Act
    await api.buildGraph(['3506003', '3550704'], true)

    // Assert
    expect(corpo.connect_components).toBe(false)
  })

  it('deve enviar o grafo do usuário quando fornecido no benchmark', async () => {
    // Arrange
    let corpo: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/benchmark', async ({ request }) => {
        corpo = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ rows: [], meta: {} })
      })
    )
    const grafo = {
      nodes: [{ id: 'A', name: 'A', lat: 0, lon: 0 }],
      edges: [{ u: 'A', v: 'A', weight: 1, attrs: {} }],
      warnings: [],
      discarded: [],
    }

    // Act
    await api.benchmark({ graph: grafo, runs: 5 })

    // Assert
    expect(corpo).toEqual({
      graph: grafo,
      runs: 5,
    })
  })

  it('deve manter chamadas fetch restritas ao client.ts', () => {
    // Arrange
    const raiz = join(process.cwd(), 'src')
    const arquivos = [
      join(raiz, 'App.vue'),
      ...readdirSync(join(raiz, 'components')).map((nome) => join(raiz, 'components', nome)),
    ]

    // Act
    const usos = arquivos.filter((arquivo) => readFileSync(arquivo, 'utf8').includes('fetch('))

    // Assert
    expect(usos).toEqual([])
  })

  it('deve expor ApiError como subclasse de Error', () => {
    // Arrange / Act
    const erro = new ApiError('x', 1, 'Y')

    // Assert
    expect(erro).toBeInstanceOf(Error)
    expect(erro.details).toEqual([])
  })
})
