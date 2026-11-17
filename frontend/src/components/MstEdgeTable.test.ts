import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import MstEdgeTable from './MstEdgeTable.vue'
import type { Edge } from '../types'

function arestas(quantidade: number): Edge[] {
  return Array.from({ length: quantidade }, (_, indice) => ({
    u: `A${indice}`,
    v: `B${indice}`,
    weight: indice + 0.5,
    attrs: { source: indice % 2 === 0 ? 'manual' : 'divisa' },
  }))
}

describe('MstEdgeTable', () => {
  it('C-39: deve informar quando nenhuma aresta foi aceita', () => {
    // Arrange / Act
    render(MstEdgeTable, { props: { edges: [], names: {} } })

    // Assert
    expect(screen.getByText('Nenhuma aresta foi aceita.')).toBeInTheDocument()
  })

  it('C-40: deve mostrar as 120 primeiras arestas e alternar para todas', async () => {
    // Arrange
    render(MstEdgeTable, { props: { edges: arestas(121), names: {} } })

    // Assert: cabeçalho + 120 linhas
    expect(screen.getAllByRole('row')).toHaveLength(121)

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Mostrar todas as 121 arestas' }))

    // Assert
    expect(screen.getAllByRole('row')).toHaveLength(122)
    expect(
      screen.getByRole('button', { name: 'Mostrar apenas as 120 primeiras' })
    ).toBeInTheDocument()
  })

  it('C-41: deve usar nome com fallback para id, badge de origem e distância formatada', () => {
    // Arrange
    const lista: Edge[] = [
      { u: 'A', v: 'B', weight: 12.3456, attrs: { source: 'manual' } },
      { u: 'B', v: 'C', weight: 0.5, attrs: { source: 'divisa' } },
    ]

    // Act
    render(MstEdgeTable, { props: { edges: lista, names: { A: 'Alfa', B: '' } } })

    // Assert: o nome e o id ficam em nós separados; compara o texto da célula
    const celulas = screen
      .getAllByRole('cell')
      .map((celula) => celula.textContent?.replace(/\s+/g, ' ').trim())
    expect(celulas).toContain('Alfa (A)')
    expect(celulas).toContain('B (B)')
    expect(screen.getByText('manual')).toBeInTheDocument()
    expect(screen.getByText('divisa')).toBeInTheDocument()
    expect(screen.getByText('12,346 km')).toBeInTheDocument()
    expect(screen.getByText('0,500 km')).toBeInTheDocument()
  })
})
