import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import MetricsTable from './MetricsTable.vue'

describe('MetricsTable', () => {
  it('C-38: deve listar as métricas de Kruskal na ordem e rótulos corretos', () => {
    // Arrange
    const metrics = {
      union_calls: 3,
      time_ms: 1.5,
      rejected: 1,
      find_calls: 6,
      accepted: 3,
      edges_examined: 4,
    }

    // Act
    render(MetricsTable, { props: { metrics, algorithm: 'kruskal' } })

    // Assert
    const rotulos = screen.getAllByRole('rowheader').map((celula) => celula.textContent)
    expect(rotulos).toEqual([
      'Tempo (sem trace)',
      'Arestas examinadas',
      'Arestas aceitas',
      'Arestas rejeitadas',
      'Chamadas a find',
      'Chamadas a union',
    ])
    expect(screen.getByText('1.50 ms')).toBeInTheDocument()
    expect(screen.queryByText('Inserções no heap')).not.toBeInTheDocument()
  })

  it('C-38: deve listar as métricas de Prim na ordem e rótulos corretos', () => {
    // Arrange
    const metrics = {
      stale_pops: 1,
      time_ms: 0.5,
      heap_pops: 4,
      heap_pushes: 5,
      accepted: 3,
      edges_examined: 3,
    }

    // Act
    render(MetricsTable, { props: { metrics, algorithm: 'prim' } })

    // Assert
    const rotulos = screen.getAllByRole('rowheader').map((celula) => celula.textContent)
    expect(rotulos).toEqual([
      'Tempo (sem trace)',
      'Arestas examinadas',
      'Arestas aceitas',
      'Inserções no heap',
      'Extrações do heap',
      'Entradas obsoletas',
    ])
    expect(screen.getByText('0.500 ms')).toBeInTheDocument()
    expect(screen.queryByText('Chamadas a find')).not.toBeInTheDocument()
  })
})
