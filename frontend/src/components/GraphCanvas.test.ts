import { fireEvent, render, screen } from '@testing-library/vue'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import GraphCanvas from './GraphCanvas.vue'
import { grafo } from '../test/fixtures'
import { context2d, limparContexto } from '../test/canvas'
import type { GraphData } from '../types'

function opcoes(overrides: Record<string, unknown> = {}) {
  return {
    graph: grafo,
    mstEdges: [],
    traceEdges: null,
    currentEdge: null,
    componentColors: null,
    startVertex: null,
    showManual: true,
    showShortBorders: true,
    ...overrides,
  }
}

function grafoCom(quantidade: number): GraphData {
  return {
    nodes: Array.from({ length: quantidade }, (_, indice) => ({
      id: `N${indice}`,
      name: `Nó ${indice}`,
      lat: -22 + indice * 0.001,
      lon: -49 + indice * 0.001,
    })),
    edges: [],
    warnings: [],
    discarded: [],
  }
}

describe('GraphCanvas', () => {
  it('C-23: deve expor canvas acessível e controles reais com rótulos', () => {
    // Arrange / Act
    render(GraphCanvas, { props: opcoes() })

    // Assert
    const canvas = screen.getByRole('img', { name: /Grafo dos municípios/ })
    expect(canvas).toHaveAttribute('aria-label')
    expect(screen.getByRole('button', { name: 'Ampliar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reduzir' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restaurar visualização' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Legenda do grafo' })).toBeInTheDocument()
  })

  it('C-24: deve respeitar os filtros de ligações manuais e divisas curtas', async () => {
    // Arrange
    const { rerender } = render(GraphCanvas, { props: opcoes() })
    await nextTick()

    // Act/Assert: todas as 3 arestas visíveis
    limparContexto()
    await rerender(opcoes())
    await nextTick()
    expect(context2d.lineTo).toHaveBeenCalledTimes(3)

    // Act: sem manuais
    limparContexto()
    await rerender(opcoes({ showManual: false }))
    await nextTick()
    expect(context2d.lineTo).toHaveBeenCalledTimes(2)

    // Act: sem divisas curtas
    limparContexto()
    await rerender(opcoes({ showShortBorders: false }))
    await nextTick()
    expect(context2d.lineTo).toHaveBeenCalledTimes(2)

    // Act: sem manuais e sem curtas
    limparContexto()
    await rerender(opcoes({ showManual: false, showShortBorders: false }))
    await nextTick()
    expect(context2d.lineTo).toHaveBeenCalledTimes(1)
  })

  it('C-25: deve redesenhar ao mudar grafo/arestas/cores e não quebrar sem contexto 2D', async () => {
    // Arrange
    const { rerender } = render(GraphCanvas, { props: opcoes() })
    await nextTick()

    // Act: mudança de grafo, MST e cores
    limparContexto()
    await rerender(
      opcoes({
        graph: { ...grafo, nodes: grafo.nodes.slice(0, 2), edges: [grafo.edges[0]] },
        mstEdges: [grafo.edges[0]],
        componentColors: { A: 0, B: 1 },
        startVertex: 'A',
      })
    )
    await nextTick()

    // Assert
    expect(context2d.clearRect).toHaveBeenCalled()
    expect(context2d.stroke).toHaveBeenCalled()

    // Act/Assert: contexto nulo não lança
    const spy = HTMLCanvasElement.prototype.getContext as unknown as {
      mockReturnValueOnce: (valor: null) => void
    }
    spy.mockReturnValueOnce(null)
    await expect(rerender(opcoes({ startVertex: 'B' }))).resolves.toBeUndefined()
  })

  it('C-26: deve ampliar, reduzir e restaurar a visualização', async () => {
    // Arrange
    render(GraphCanvas, { props: opcoes() })
    await nextTick()

    // Posição inicial do primeiro vértice
    limparContexto()
    await fireEvent.click(screen.getByRole('button', { name: 'Restaurar visualização' }))
    await nextTick()
    const inicial = (context2d.arc.mock.calls[0] as number[]).slice(0, 2)

    // Act: amplia
    limparContexto()
    await fireEvent.click(screen.getByRole('button', { name: 'Ampliar' }))
    await nextTick()
    const ampliado = (context2d.arc.mock.calls[0] as number[]).slice(0, 2)

    // Assert: a posição muda com o zoom
    expect(ampliado).not.toEqual(inicial)

    // Act: restaura
    limparContexto()
    await fireEvent.click(screen.getByRole('button', { name: 'Restaurar visualização' }))
    await nextTick()
    const restaurado = (context2d.arc.mock.calls[0] as number[]).slice(0, 2)

    // Assert
    expect(restaurado[0]).toBeCloseTo(inicial[0], 5)
    expect(restaurado[1]).toBeCloseTo(inicial[1], 5)

    // Act: roda do mouse com limites não deve lançar
    await fireEvent.wheel(screen.getByRole('img'), { deltaY: -10000 })
    await fireEvent.wheel(screen.getByRole('img'), { deltaY: 10000 })
  })

  it('C-27: deve mostrar tooltip com nome, id e grau do vértice sob o mouse', async () => {
    // Arrange
    render(GraphCanvas, { props: opcoes() })
    await nextTick()
    const [x, y] = (context2d.arc.mock.calls[0] as number[]).slice(0, 2)
    const canvas = screen.getByRole('img')

    // Act
    await fireEvent.pointerMove(canvas, { clientX: x, clientY: y })

    // Assert
    expect(await screen.findByText('Alfa')).toBeInTheDocument()
    expect(screen.getByText(/A · grau 1/)).toBeInTheDocument()
  })

  it('C-28: deve mostrar todos os rótulos até 30 vértices e ocultá-los acima disso', async () => {
    // Arrange
    const { rerender } = render(GraphCanvas, { props: opcoes() })
    await nextTick()

    // Assert: 4 vértices -> todos os nomes desenhados
    limparContexto()
    await rerender(opcoes())
    await nextTick()
    const rotulos = context2d.fillText.mock.calls.map((chamada) => chamada[0])
    expect(rotulos).toContain('Alfa')
    expect(rotulos).toContain('Delta')

    // Act: 31 vértices sem início/hover
    limparContexto()
    await rerender(opcoes({ graph: grafoCom(31) }))
    await nextTick()

    // Assert: nenhum rótulo fixo
    expect(context2d.fillText).not.toHaveBeenCalled()
  })
})
