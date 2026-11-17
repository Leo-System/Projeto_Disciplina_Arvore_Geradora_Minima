import { fireEvent, render, screen } from '@testing-library/vue'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it } from 'vitest'
import BenchmarkChart from './BenchmarkChart.vue'
import { linhasBenchmark } from '../test/fixtures'
import { context2d, limparContexto } from '../test/canvas'
import type { BenchmarkRow } from '../types'

describe('BenchmarkChart', () => {
  beforeEach(() => {
    limparContexto()
  })

  it('C-54: deve exibir mensagem quando não há dados', () => {
    // Arrange / Act
    render(BenchmarkChart, { props: { rows: [] } })

    // Assert
    const textos = context2d.fillText.mock.calls.map((chamada) => chamada[0])
    expect(textos).toContain('Sem dados de benchmark.')
  })

  it('C-55: deve desenhar eixos, legenda, faixas p25–p75 e linhas em escala log', async () => {
    // Arrange / Act
    render(BenchmarkChart, { props: { rows: linhasBenchmark } })
    await nextTick()

    // Assert
    const textos = context2d.fillText.mock.calls.map((chamada) => chamada[0])
    expect(textos).toContain('vértices (escala logarítmica)')
    expect(textos).toContain('tempo (ms)')
    expect(textos).toContain('Kruskal')
    expect(textos).toContain('Prim')
    expect(textos).toContain('faixa = p25–p75 · ponto = mediana')
    expect(context2d.stroke).toHaveBeenCalled()
    expect(context2d.moveTo).toHaveBeenCalled()
    expect(context2d.lineTo).toHaveBeenCalled()
    expect(context2d.arc).toHaveBeenCalled()
  })

  it('C-55: não deve quebrar com valores zero', async () => {
    // Arrange
    const zeros: BenchmarkRow[] = [
      {
        n_nodes: 10,
        n_edges: 9,
        kruskal_ms: 0,
        kruskal_p25_ms: 0,
        kruskal_p75_ms: 0,
        prim_ms: 0,
        prim_p25_ms: 0,
        prim_p75_ms: 0,
      },
    ]

    // Act
    render(BenchmarkChart, { props: { rows: zeros } })
    await nextTick()

    // Assert
    expect(context2d.fillText).toHaveBeenCalled()
  })

  it('C-56: deve mostrar tooltip ao passar o mouse sobre um ponto', async () => {
    // Arrange
    render(BenchmarkChart, { props: { rows: linhasBenchmark } })
    await nextTick()
    const ponto = context2d.arc.mock.calls[0] as number[]
    const canvas = screen.getByRole('img', { name: /Gráfico de linhas/ })

    // Act
    await fireEvent.mouseMove(canvas, { clientX: ponto[0], clientY: ponto[1] })

    // Assert
    expect(await screen.findByText(/8 vértices · 15 arestas/)).toBeInTheDocument()
    expect(screen.getByText(/Kruskal:/)).toBeInTheDocument()
  })
})
