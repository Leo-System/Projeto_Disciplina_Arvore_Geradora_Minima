import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import ComparisonPanel from './ComparisonPanel.vue'
import { comparacao, criarResultado } from '../test/fixtures'
import type { Edge } from '../types'

const nomes = { A: 'Alfa', B: 'Beta', C: 'Gama', D: 'Delta' }

describe('ComparisonPanel', () => {
  it('C-42: deve exibir estado vazio sem comparação ou sem os dois resultados', () => {
    // Arrange / Act: sem comparação
    const { unmount } = render(ComparisonPanel, {
      props: { kruskal: null, prim: null, comparison: null, names: {} },
    })

    // Assert
    expect(screen.getByText('Comparação indisponível')).toBeInTheDocument()
    unmount()

    // Act: comparação presente, mas nenhum algoritmo executado
    render(ComparisonPanel, {
      props: { kruskal: null, prim: null, comparison: comparacao, names: nomes },
    })

    // Assert
    expect(screen.getByText('Comparação indisponível')).toBeInTheDocument()
  })

  it('C-43: deve exibir cards, fatos e custos dos dois algoritmos', () => {
    // Arrange
    const kruskal = criarResultado('kruskal')
    const prim = criarResultado('prim', { total_cost: 4 })

    // Act
    render(ComparisonPanel, { props: { kruskal, prim, comparison: comparacao, names: nomes } })

    // Assert
    expect(screen.getByRole('heading', { name: 'Kruskal' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Prim' })).toBeInTheDocument()
    expect(screen.getAllByText('4,000 km')).toHaveLength(2)
    expect(screen.getAllByText('Sim')).toHaveLength(2)
    expect(screen.getByText('Não')).toBeInTheDocument()
    expect(screen.getByText('Diferença de custo')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Complexidades teóricas' })).toBeInTheDocument()
  })

  it('C-44: deve listar arestas exclusivas de cada algoritmo', () => {
    // Arrange
    const soKruskal: Edge[] = [{ u: 'A', v: 'B', weight: 1, attrs: { source: 'divisa' } }]
    const soPrim: Edge[] = [{ u: 'C', v: 'D', weight: 2, attrs: { source: 'divisa' } }]
    const comparison = {
      ...comparacao,
      same_edges: false,
      kruskal_only_edges: soKruskal,
      prim_only_edges: soPrim,
    }

    // Act
    render(ComparisonPanel, {
      props: {
        kruskal: criarResultado('kruskal'),
        prim: criarResultado('prim'),
        comparison,
        names: nomes,
      },
    })

    // Assert
    expect(screen.getByRole('heading', { name: 'Só em Kruskal' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Só em Prim' })).toBeInTheDocument()
    expect(screen.getByText(/Alfa — Beta/)).toBeInTheDocument()
    expect(screen.getByText(/Gama — Delta/)).toBeInTheDocument()
  })

  it('C-45: não deve exibir diferença enganosa de 0,000 km para custos quase iguais', () => {
    // Arrange: diferença positiva que arredonda para 0,000 km (BUG-018)
    const comparison = { ...comparacao, cost_difference: 0.0004 }

    // Act
    render(ComparisonPanel, {
      props: {
        kruskal: criarResultado('kruskal'),
        prim: criarResultado('prim'),
        comparison,
        names: nomes,
      },
    })

    // Assert
    expect(screen.queryByText('0,000 km')).not.toBeInTheDocument()
  })
})
