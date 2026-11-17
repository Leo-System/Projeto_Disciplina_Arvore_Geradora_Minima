import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import App from './App.vue'
import { server } from './test/server'
import { context2d } from './test/canvas'
import {
  benchmark,
  cidades,
  criarExecucao,
  criarResultado,
  eventosTrace,
  grafo,
  verificacao,
} from './test/fixtures'
import type { PresetDetail, PresetSummary, RunResponse } from './types'

const presets: PresetSummary[] = [
  {
    id: 'p1-bauru-vizinhos',
    name: 'p1 — Bauru e vizinhos',
    description: 'Bauru e municípios do entorno.',
    n_nodes: 4,
    n_edges: 3,
    n_components: 1,
    include_manual: true,
  },
  {
    id: 'p3-estado-sp',
    name: 'p3 — Estado de São Paulo (maior componente)',
    description: 'Maior componente sem a ligação manual.',
    n_nodes: 644,
    n_edges: 1832,
    n_components: 1,
    include_manual: false,
  },
]

function detalhe(id: string): PresetDetail {
  const resumo = presets.find((preset) => preset.id === id) ?? presets[0]
  return {
    id: resumo.id,
    name: resumo.name,
    description: resumo.description,
    include_manual: resumo.include_manual,
    graph: grafo,
  }
}

function execucaoSemTrace(): RunResponse {
  return criarExecucao({
    kruskal: criarResultado('kruskal', { trace: null }),
    prim: criarResultado('prim', { trace: null }),
  })
}

function execucaoComTrace(): RunResponse {
  return criarExecucao({
    kruskal: criarResultado('kruskal', { trace: eventosTrace }),
    prim: criarResultado('prim', { trace: eventosTrace }),
  })
}

interface ControleApi {
  corposExecucao: Array<Record<string, unknown>>
  corposBuild: Array<Record<string, unknown>>
  detalhesPreset: string[]
}

function instalarApi(): ControleApi {
  const controle: ControleApi = { corposExecucao: [], corposBuild: [], detalhesPreset: [] }
  server.use(
    http.get('*/api/v1/cities', () => HttpResponse.json({ cities: cidades })),
    http.get('*/api/v1/presets', () => HttpResponse.json({ presets })),
    http.get('*/api/v1/presets/:id', ({ params }) => {
      const id = String(params.id)
      controle.detalhesPreset.push(id)
      return HttpResponse.json(detalhe(id))
    }),
    http.post('*/api/v1/run', async ({ request }) => {
      const corpo = (await request.json()) as Record<string, unknown>
      controle.corposExecucao.push(corpo)
      const base = corpo.trace ? execucaoComTrace() : execucaoSemTrace()
      if (corpo.algorithm === 'kruskal') return HttpResponse.json({ ...base, prim: null })
      if (corpo.algorithm === 'prim') return HttpResponse.json({ ...base, kruskal: null })
      return HttpResponse.json(base)
    }),
    http.post('*/api/v1/graph/build', async ({ request }) => {
      controle.corposBuild.push((await request.json()) as Record<string, unknown>)
      return HttpResponse.json(grafo)
    }),
    http.post('*/api/v1/graph/upload', () => HttpResponse.json({ graph: grafo })),
    http.post('*/api/v1/benchmark', () => HttpResponse.json(benchmark))
  )
  return controle
}

async function aguardarBoot(): Promise<void> {
  expect(await screen.findByText('p1 — Bauru e vizinhos')).toBeInTheDocument()
  expect(await screen.findByRole('heading', { name: 'Métricas de Kruskal' })).toBeInTheDocument()
  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'Executar algoritmos' })).toBeEnabled()
  })
  await waitFor(() => {
    expect(screen.queryByText('Carregando o grafo…')).not.toBeInTheDocument()
  })
}

function grupo(nome: string): HTMLElement {
  return screen.getByRole('group', { name: nome })
}

describe('App', () => {
  it('C-01: deve carregar cidades/presets, selecionar p1 e executar automaticamente', async () => {
    // Arrange
    const controle = instalarApi()

    // Act
    render(App)

    // Assert
    await aguardarBoot()
    expect(screen.getByText('3 municípios')).toBeInTheDocument()
    expect(screen.getByText('4 vértices')).toBeInTheDocument()
    expect(screen.getByText('3 arestas')).toBeInTheDocument()
    expect(screen.getAllByText('4,000 km').length).toBeGreaterThan(0)
    expect(controle.corposExecucao).toHaveLength(1)
    expect(controle.corposExecucao[0].algorithm).toBe('both')
  })

  it('C-02: deve exibir banner de erro quando o boot falha', async () => {
    // Arrange
    instalarApi()
    server.use(
      http.get('*/api/v1/cities', () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'Falha ao carregar cidades', details: [] } },
          { status: 500 }
        )
      )
    )

    // Act
    render(App)

    // Assert
    const banner = await screen.findByRole('alert')
    expect(banner).toHaveTextContent('Falha ao carregar cidades')
    expect(screen.queryByText('4,000 km')).not.toBeInTheDocument()
  })

  it('C-03: deve carregar e executar ao escolher outro preset', async () => {
    // Arrange
    const controle = instalarApi()
    render(App)
    await aguardarBoot()

    // Act
    await fireEvent.click(screen.getByRole('button', { name: /p3 — Estado de São Paulo/ }))

    // Assert
    expect(
      await screen.findByRole('heading', {
        name: 'p3 — Estado de São Paulo (maior componente)',
      })
    ).toBeInTheDocument()
    expect(screen.getAllByText('Maior componente sem a ligação manual.').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /p3 — Estado de São Paulo/ })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    await waitFor(() => expect(controle.corposExecucao).toHaveLength(2))
  })

  it('C-04: deve alternar modo de seleção/upload e limpar erros', async () => {
    // Arrange: boot falha e deixa banner
    instalarApi()
    server.use(
      http.get('*/api/v1/cities', () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'Falha inicial', details: [] } },
          { status: 500 }
        )
      )
    )
    render(App)
    await screen.findByRole('alert')

    // Act: seleção
    await fireEvent.click(screen.getByRole('button', { name: 'Selecionar' }))

    // Assert
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Buscar município por nome ou código IBGE/i)).toBeInTheDocument()

    // Act: arquivo
    await fireEvent.click(screen.getByRole('button', { name: 'Arquivo' }))

    // Assert
    expect(screen.getByRole('button', { name: 'Escolher arquivo' })).toBeInTheDocument()
    expect(screen.getByText(/Arraste um arquivo CSV ou JSON/)).toBeInTheDocument()
  })

  it('C-05: deve desabilitar o botão durante a execução e não enviar duplicado', async () => {
    // Arrange
    const controle = instalarApi()
    let liberar: (() => void) | null = null
    let chamadas = 0
    server.use(
      http.post('*/api/v1/run', async ({ request }) => {
        const corpo = (await request.json()) as Record<string, unknown>
        controle.corposExecucao.push(corpo)
        chamadas += 1
        if (chamadas > 1) await new Promise<void>((resolve) => (liberar = resolve))
        return HttpResponse.json(execucaoComTrace())
      })
    )
    render(App)
    await aguardarBoot()

    // Act
    const botao = screen.getByRole('button', { name: 'Executar algoritmos' })
    await fireEvent.click(botao)

    // Assert
    const executando = await screen.findByRole('button', { name: 'Executando…' })
    expect(executando).toBeDisabled()
    expect(screen.getByText(/Executando Kruskal e Prim/)).toBeInTheDocument()
    await waitFor(() => expect(chamadas).toBe(2))

    // Act: clique repetido durante loading
    await fireEvent.click(executando)
    await waitFor(() => expect(liberar).not.toBeNull())
    expect(chamadas).toBe(2)

    // Act / Assert: conclui
    liberar!()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Executar algoritmos' })).toBeEnabled()
    })
  })

  it('C-06: deve enviar start_vertex apenas fora do Kruskal e desabilitar o seletor', async () => {
    // Arrange
    const controle = instalarApi()
    render(App)
    await aguardarBoot()
    const seletor = screen.getByLabelText('Vértice inicial do Prim') as HTMLSelectElement
    controle.corposExecucao.length = 0

    // Act: Kruskal
    await fireEvent.click(
      within(grupo('Algoritmo a executar')).getByRole('button', { name: 'Kruskal' })
    )
    expect(seletor).toBeDisabled()
    await fireEvent.click(screen.getByRole('button', { name: 'Executar algoritmos' }))
    await waitFor(() => expect(controle.corposExecucao).toHaveLength(1))

    // Assert
    expect(controle.corposExecucao[0]).toMatchObject({ algorithm: 'kruskal', start_vertex: null })

    // Act: Prim com início escolhido
    await fireEvent.click(
      within(grupo('Algoritmo a executar')).getByRole('button', { name: 'Prim' })
    )
    expect(seletor).toBeEnabled()
    await fireEvent.update(seletor, 'A')
    await fireEvent.click(screen.getByRole('button', { name: 'Executar algoritmos' }))
    await waitFor(() => expect(controle.corposExecucao).toHaveLength(2))

    // Assert
    expect(controle.corposExecucao[1]).toMatchObject({ algorithm: 'prim', start_vertex: 'A' })
  })

  it('C-07: deve definir o início do Prim ao clicar em um vértice e mudar para Ambos', async () => {
    // Arrange
    instalarApi()
    render(App)
    await aguardarBoot()
    await fireEvent.click(
      within(grupo('Algoritmo a executar')).getByRole('button', { name: 'Kruskal' })
    )
    const canvas = screen.getByRole('img', { name: /Grafo dos municípios/ })
    const chamadas = context2d.arc.mock.calls
    const [x, y] = chamadas[chamadas.length - 4] as number[]

    // Act
    await fireEvent.pointerDown(canvas, { clientX: x, clientY: y, pointerId: 1 })
    await fireEvent.pointerUp(canvas, { clientX: x, clientY: y, pointerId: 1 })

    // Assert
    expect(
      within(grupo('Algoritmo a executar')).getByRole('button', { name: 'Ambos' })
    ).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByLabelText('Vértice inicial do Prim')).toHaveValue('A')
  })

  it('C-08: deve ignorar nova carga de grafo enquanto uma está em andamento', async () => {
    // Arrange
    const controle = instalarApi()
    render(App)
    await aguardarBoot()
    let liberar: (() => void) | null = null
    server.use(
      http.get('*/api/v1/presets/:id', async ({ params }) => {
        controle.detalhesPreset.push(String(params.id))
        await new Promise<void>((resolve) => (liberar = resolve))
        return HttpResponse.json(detalhe(String(params.id)))
      })
    )

    // Act: inicia p3
    await fireEvent.click(screen.getByRole('button', { name: /p3 — Estado de São Paulo/ }))
    expect(await screen.findByText('Carregando o grafo…')).toBeInTheDocument()
    await waitFor(() => expect(controle.detalhesPreset).toContain('p3-estado-sp'))

    // Act: tenta p1 durante o carregamento
    await fireEvent.click(screen.getByRole('button', { name: /p1 — Bauru e vizinhos/ }))

    // Assert: apenas o p3 foi solicitado
    expect(controle.detalhesPreset).toEqual(['p1-bauru-vizinhos', 'p3-estado-sp'])

    // Act / Assert: conclui a carga pendente
    await waitFor(() => expect(liberar).not.toBeNull())
    liberar!()
    expect(
      await screen.findByRole('heading', {
        name: 'p3 — Estado de São Paulo (maior componente)',
      })
    ).toBeInTheDocument()
  })

  it('C-09: deve trocar de abas e mostrar o contador de eventos no passo a passo', async () => {
    // Arrange
    instalarApi()
    render(App)
    await aguardarBoot()
    const abaPasso = screen.getByRole('tab', { name: /Passo a passo/ })
    expect(abaPasso).toHaveTextContent('4')

    // Act
    await fireEvent.click(abaPasso)

    // Assert
    expect(abaPasso).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: /Passo a passo — Kruskal/ })).toBeInTheDocument()
    expect(document.getElementById('panel-passo')?.style.display).toBe('')

    // Act / Assert: teoria e modelagem
    await fireEvent.click(screen.getByRole('tab', { name: 'Teoria' }))
    expect(screen.getByRole('heading', { name: 'Árvore geradora mínima' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('tab', { name: 'Modelagem' }))
    expect(screen.getByRole('heading', { name: 'Modelagem do grafo' })).toBeInTheDocument()
  })

  it('C-10: deve orientar quando não há trace e permitir executar com passo a passo', async () => {
    // Arrange
    instalarApi()
    render(App)
    await aguardarBoot()
    await fireEvent.click(screen.getByLabelText('Gerar passo a passo'))
    await fireEvent.click(screen.getByRole('button', { name: 'Executar algoritmos' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Executar algoritmos' })).toBeEnabled()
    })

    // Act
    await fireEvent.click(screen.getByRole('tab', { name: /Passo a passo/ }))

    // Assert
    expect(screen.getByText('Passo a passo indisponível')).toBeInTheDocument()
    expect(screen.getByText(/A última execução foi feita sem o rastro/)).toBeInTheDocument()

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar com passo a passo' }))

    // Assert
    expect(
      await screen.findByRole('heading', { name: /Passo a passo — Kruskal/ })
    ).toBeInTheDocument()
  })

  it('C-11: deve alternar resultado Kruskal/Prim e exibir floresta quando desconexo', async () => {
    // Arrange
    instalarApi()
    server.use(
      http.post('*/api/v1/run', () =>
        HttpResponse.json(
          criarExecucao({
            kruskal: criarResultado('kruskal', {
              n_components: 2,
              components: [
                { size: 3, node_ids: ['A', 'B', 'C'] },
                { size: 1, node_ids: ['D'] },
              ],
              trace: eventosTrace,
            }),
            prim: criarResultado('prim', { trace: eventosTrace }),
            verification: { kruskal: verificacao, prim: verificacao },
          })
        )
      )
    )
    render(App)
    await aguardarBoot()

    // Assert: floresta
    expect(screen.getAllByText(/floresta geradora mínima/i).length).toBeGreaterThan(0)

    // Act: alterna para Prim
    await fireEvent.click(within(grupo('Resultado exibido')).getByRole('button', { name: 'Prim' }))

    // Assert
    expect(screen.getByRole('heading', { name: 'Métricas de Prim' })).toBeInTheDocument()

    // Act: volta para Kruskal
    await fireEvent.click(
      within(grupo('Resultado exibido')).getByRole('button', { name: 'Kruskal' })
    )

    // Assert
    expect(screen.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeInTheDocument()
  })

  it('C-12: deve repassar avisos e descartados do grafo ao WarningsPanel', async () => {
    // Arrange
    instalarApi()

    // Act
    render(App)
    await aguardarBoot()

    // Assert
    expect(screen.getByRole('heading', { name: 'Avisos' })).toBeInTheDocument()
    expect(screen.getByText('Grafo de teste com aviso.')).toBeInTheDocument()
    expect(screen.getAllByText(/Ilhabela/).length).toBeGreaterThan(0)
  })

  it('C-61: deve cobrir loading, sucesso e erro na mesma tela', async () => {
    // Arrange: boot pendente
    instalarApi()
    let liberar: (() => void) | null = null
    server.use(
      http.get('*/api/v1/cities', async () => {
        await new Promise<void>((resolve) => (liberar = resolve))
        return HttpResponse.json({ cities: cidades })
      })
    )

    // Act
    render(App)

    // Assert: loading
    expect(
      await screen.findByText(/Carregando municípios, instâncias e o resultado inicial/)
    ).toBeInTheDocument()

    // Act: sucesso
    await waitFor(() => expect(liberar).not.toBeNull())
    liberar!()
    await screen.findByText('p1 — Bauru e vizinhos')

    // Arrange: próxima execução falha
    server.use(
      http.post('*/api/v1/run', () =>
        HttpResponse.json(
          { error: { code: 'VALIDATION_ERROR', message: 'Falha controlada', details: ['x'] } },
          { status: 422 }
        )
      )
    )

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar algoritmos' }))

    // Assert: erro
    const banner = await screen.findByRole('alert')
    expect(banner).toHaveTextContent('Falha controlada')
    expect(banner).toHaveTextContent('x')
  })

  it('C-62: não deve enviar execução duplicada em cliques repetidos', async () => {
    // Arrange
    const controle = instalarApi()
    let liberar: (() => void) | null = null
    let chamadas = 0
    server.use(
      http.post('*/api/v1/run', async ({ request }) => {
        controle.corposExecucao.push((await request.json()) as Record<string, unknown>)
        chamadas += 1
        if (chamadas > 1) await new Promise<void>((resolve) => (liberar = resolve))
        return HttpResponse.json(execucaoComTrace())
      })
    )
    render(App)
    await aguardarBoot()

    // Act: três cliques durante o carregamento
    const botao = screen.getByRole('button', { name: 'Executar algoritmos' })
    await fireEvent.click(botao)
    const executando = await screen.findByRole('button', { name: 'Executando…' })
    await fireEvent.click(executando)
    await fireEvent.click(executando)

    // Assert: apenas a execução inicial + uma manual
    await waitFor(() => expect(chamadas).toBe(2))
    await waitFor(() => expect(liberar).not.toBeNull())
    expect(chamadas).toBe(2)

    liberar!()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Executar algoritmos' })).toBeEnabled()
    })
  })

  function selecionarCidade(nomeOuId: string): void {
    const checkboxes = screen.getAllByRole('checkbox')
    const alvo = checkboxes.find((cb) => {
      const container = cb.closest('.city-option') ?? cb.parentElement
      return container?.textContent?.includes(nomeOuId)
    })
    expect(alvo).toBeDefined()
    fireEvent.click(alvo!)
    fireEvent.change(alvo!, { target: { checked: true } })
  }

  async function entrarSelecaoESelecionarDuas(): Promise<void> {
    await fireEvent.click(screen.getByRole('button', { name: 'Selecionar' }))
    await screen.findByLabelText(/Buscar município por nome ou código IBGE/i)
    selecionarCidade('3506003') // Bauru
    await waitFor(() => {
      const summary = document.querySelector('.selection-summary')?.textContent ?? ''
      expect(summary).toContain('1 selecionado')
    })
    selecionarCidade('3505500') // São Sebastião
    await waitFor(() => {
      const summary = document.querySelector('.selection-summary')?.textContent ?? ''
      expect(summary).toContain('2 selecionado')
    })
  }

  it('C-63: toggle de conexão só aparece no modo Selecionar', async () => {
    // Arrange
    instalarApi()
    render(App)
    await aguardarBoot()

    // Assert: no boot (preset), o toggle não existe
    expect(
      screen.queryByText(/Conectar as cidades selecionadas em um único grafo/)
    ).not.toBeInTheDocument()

    // Act: muda para Selecionar
    await fireEvent.click(screen.getByRole('button', { name: 'Selecionar' }))

    // Assert: o toggle aparece
    expect(
      screen.getByText(/Conectar as cidades selecionadas em um único grafo/)
    ).toBeInTheDocument()
  })

  it('C-64: toggle desmarcado envia connect_components: false', async () => {
    // Arrange
    const controle = instalarApi()
    render(App)
    await aguardarBoot()
    await entrarSelecaoESelecionarDuas()

    // Assert: duas cidades selecionadas -> botão habilitado
    expect(screen.getByRole('button', { name: 'Montar grafo (2)' })).toBeInTheDocument()

    // Act: monta o grafo (toggle fica desmarcado)
    await fireEvent.click(screen.getByRole('button', { name: 'Montar grafo (2)' }))
    await waitFor(() => expect(controle.corposBuild).toHaveLength(1))

    // Assert
    expect(controle.corposBuild[0]).toMatchObject({
      city_ids: expect.arrayContaining(['3506003', '3505500']),
      connect_components: false,
    })
  })

  it('C-65: toggle marcado envia connect_components: true', async () => {
    // Arrange
    const controle = instalarApi()
    render(App)
    await aguardarBoot()
    await entrarSelecaoESelecionarDuas()

    // Assert: duas cidades selecionadas
    expect(screen.getByRole('button', { name: 'Montar grafo (2)' })).toBeInTheDocument()

    // Act: marca o toggle e monta o grafo
    await fireEvent.click(
      screen.getByRole('checkbox', { name: /Conectar as cidades selecionadas/ })
    )
    await fireEvent.click(screen.getByRole('button', { name: 'Montar grafo (2)' }))
    await waitFor(() => expect(controle.corposBuild).toHaveLength(1))

    // Assert
    expect(controle.corposBuild[0]).toMatchObject({
      city_ids: expect.arrayContaining(['3506003', '3505500']),
      connect_components: true,
    })
  })

  it('C-66: alterar o toggle não remonta o grafo automaticamente', async () => {
    // Arrange
    const controle = instalarApi()
    render(App)
    await aguardarBoot()
    await entrarSelecaoESelecionarDuas()

    // Assert: duas cidades selecionadas
    expect(screen.getByRole('button', { name: 'Montar grafo (2)' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Montar grafo (2)' }))
    await waitFor(() => expect(controle.corposBuild).toHaveLength(1))

    const buildsAntes = controle.corposBuild.length

    // Act: alterna o toggle sem clicar em Montar grafo
    await fireEvent.click(
      screen.getByRole('checkbox', { name: /Conectar as cidades selecionadas/ })
    )

    // Assert: nenhuma nova montagem foi disparada
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(controle.corposBuild).toHaveLength(buildsAntes)

    // Act: clica em Montar grafo novamente
    await fireEvent.click(screen.getByRole('button', { name: /Montar grafo/ }))
    await waitFor(() => expect(controle.corposBuild).toHaveLength(buildsAntes + 1))
  })
})
