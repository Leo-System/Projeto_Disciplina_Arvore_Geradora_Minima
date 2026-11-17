import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import BenchmarkPanel from './BenchmarkPanel.vue'
import { server } from '../test/server'
import { benchmark } from '../test/fixtures'

function responderComBenchmark(): void {
  server.use(http.post('*/api/v1/benchmark', () => HttpResponse.json(benchmark)))
}

describe('BenchmarkPanel', () => {
  it('C-48: deve exibir estado inicial orientando executar', () => {
    // Arrange / Act
    render(BenchmarkPanel)

    // Assert
    expect(screen.getByText('Nenhuma medição ainda')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Executar benchmark' })).toBeEnabled()
  })

  it('C-49: deve mostrar "Medindo…" e desabilitar o botão durante a execução', async () => {
    // Arrange
    let liberar: (() => void) | null = null
    server.use(
      http.post('*/api/v1/benchmark', async () => {
        await new Promise<void>((resolve) => {
          liberar = resolve
        })
        return HttpResponse.json(benchmark)
      })
    )
    render(BenchmarkPanel)

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))

    // Assert
    const botao = screen.getByRole('button', { name: 'Medindo…' })
    expect(botao).toBeDisabled()
    await waitFor(() => expect(liberar).not.toBeNull())

    // Act / Assert: conclui
    liberar!()
    expect(await screen.findByText(benchmark.meta.preset_name)).toBeInTheDocument()
  })

  it('C-50: deve exibir banner de erro com mensagem e detalhes', async () => {
    // Arrange
    server.use(
      http.post('*/api/v1/benchmark', () =>
        HttpResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'Falha ao medir o benchmark.',
              details: ['preset inválido'],
            },
          },
          { status: 422 }
        )
      )
    )
    render(BenchmarkPanel)

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))

    // Assert
    const banner = await screen.findByRole('alert')
    expect(banner).toHaveTextContent('Falha ao medir o benchmark.')
    expect(banner).toHaveTextContent('preset inválido')
  })

  it('C-51: deve exibir meta, gráfico e tabela com sete linhas no sucesso', async () => {
    // Arrange
    responderComBenchmark()
    render(BenchmarkPanel)

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))

    // Assert
    expect(await screen.findByText(benchmark.meta.preset_name)).toBeInTheDocument()
    expect(screen.getByText(/início em Bauru/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Gráfico de linhas/ })).toBeInTheDocument()
    // cabeçalho + 7 linhas
    expect(screen.getAllByRole('row')).toHaveLength(8)
    expect(screen.getByText(benchmark.meta.note)).toBeInTheDocument()
  })

  it('C-51: deve usar o rótulo do grafo e omitir o início quando não há cidade inicial', async () => {
    // Arrange: medição do grafo do usuário (sem cidade inicial)
    server.use(
      http.post('*/api/v1/benchmark', () =>
        HttpResponse.json({
          ...benchmark,
          meta: {
            ...benchmark.meta,
            preset_id: 'user-graph',
            preset_name: 'Grafo do usuário',
            start_city: '',
            start_city_name: '',
          },
        })
      )
    )
    render(BenchmarkPanel, {
      props: { graph: null, graphLabel: 'Seleção de 30 municípios' },
    })

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))

    // Assert
    expect(await screen.findByText('Seleção de 30 municípios')).toBeInTheDocument()
    expect(screen.queryByText(/início em/)).not.toBeInTheDocument()
    expect(screen.getByText(/644 vértices/)).toBeInTheDocument()
    expect(screen.getByText(/1\.832 arestas/)).toBeInTheDocument()
  })

  it('C-52: deve exibir indicador de loading também na reexecução com dados antigos', async () => {
    // Arrange: primeira execução concluída
    responderComBenchmark()
    render(BenchmarkPanel)
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))
    await screen.findByText(benchmark.meta.preset_name)

    // Arrange: segunda execução pendente
    let liberar: (() => void) | null = null
    server.use(
      http.post('*/api/v1/benchmark', async () => {
        await new Promise<void>((resolve) => {
          liberar = resolve
        })
        return HttpResponse.json(benchmark)
      })
    )

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))
    await waitFor(() => expect(liberar).not.toBeNull())

    // Assert: deve haver um indicador de loading visível (BUG-017; C-49 define
    // o botão "Medindo…" desabilitado como o indicador de loading)
    expect(screen.getByRole('button', { name: 'Medindo…' })).toBeDisabled()

    liberar!()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Executar benchmark' })).toBeEnabled()
    })
  })

  function instalarCaptura(): Array<Record<string, unknown>> {
    const corpos: Array<Record<string, unknown>> = []
    server.use(
      http.post('*/api/v1/benchmark', async ({ request }) => {
        corpos.push((await request.json()) as Record<string, unknown>)
        return HttpResponse.json(benchmark)
      })
    )
    return corpos
  }

  it('C-53: deve limitar runs ao máximo de 100', async () => {
    // Arrange
    const corpos = instalarCaptura()
    render(BenchmarkPanel)
    const campo = screen.getByLabelText(/Execuções por tamanho/i) as HTMLInputElement

    // Act
    await fireEvent.input(campo, { target: { value: '101' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))
    await waitFor(() => expect(corpos).toHaveLength(1))

    // Assert
    expect(corpos[0].runs).toBe(100)
    expect(campo.value).toBe('100')
  })

  it('C-53: deve arredondar o número de execuções', async () => {
    // Arrange
    const corpos = instalarCaptura()
    render(BenchmarkPanel)
    const campo = screen.getByLabelText(/Execuções por tamanho/i) as HTMLInputElement

    // Act
    await fireEvent.input(campo, { target: { value: '5.6' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))
    await waitFor(() => expect(corpos).toHaveLength(1))

    // Assert
    expect(corpos[0].runs).toBe(6)
    expect(campo.value).toBe('6')
  })

  it('C-53: deve limitar runs ao mínimo de 1 (incluindo zero)', async () => {
    // Arrange
    const corpos = instalarCaptura()
    render(BenchmarkPanel)
    const campo = screen.getByLabelText(/Execuções por tamanho/i) as HTMLInputElement

    // Act
    await fireEvent.input(campo, { target: { value: '0' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Executar benchmark' }))
    await waitFor(() => expect(corpos).toHaveLength(1))

    // Assert
    expect(corpos[0].runs).toBe(1)
    expect(campo.value).toBe('1')
  })
})
