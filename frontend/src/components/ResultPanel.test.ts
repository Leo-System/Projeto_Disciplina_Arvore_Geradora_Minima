import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import ResultPanel from './ResultPanel.vue'
import { criarResultado, verificacao } from '../test/fixtures'

const nomes = { A: 'Alfa', B: 'Beta', C: 'Gama', D: 'Delta' }

describe('ResultPanel', () => {
  it('C-34: deve orientar a execução quando não há resultado', () => {
    // Arrange / Act
    render(ResultPanel, { props: { result: null, verification: null, names: {} } })

    // Assert
    expect(screen.getByText('Nenhuma execução ainda')).toBeInTheDocument()
    expect(screen.getByText(/clique em/i)).toBeInTheDocument()
  })

  it('C-35: deve exibir custo, arestas, componentes, tempo, métricas e tabela', () => {
    // Arrange
    const result = criarResultado('kruskal')

    // Act
    render(ResultPanel, { props: { result, verification: null, names: nomes } })

    // Assert
    expect(screen.getByText('4,000 km')).toBeInTheDocument()
    expect(screen.getAllByText('Arestas aceitas').length).toBeGreaterThan(0)
    expect(screen.getAllByText('0.250 ms').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeInTheDocument()
    expect(screen.getByText('Arestas examinadas')).toBeInTheDocument()
    const celulas = screen
      .getAllByRole('cell')
      .map((celula) => celula.textContent?.replace(/\s+/g, ' ').trim())
    expect(celulas).toContain('Alfa (A)')
    expect(celulas).toContain('Beta (B)')
  })

  it('C-36: deve avisar floresta desconexa e listar tamanhos dos componentes', () => {
    // Arrange
    const result = criarResultado('prim', {
      n_components: 2,
      edges: [criarResultado('prim').edges[0]],
      components: [
        { size: 3, node_ids: ['A', 'B', 'C'] },
        { size: 1, node_ids: ['D'] },
      ],
    })

    // Act
    render(ResultPanel, { props: { result, verification: null, names: nomes } })

    // Assert
    expect(screen.getByText(/floresta geradora mínima/i)).toBeInTheDocument()
    expect(screen.getByText(/1 arestas \(n − c\)/i)).toBeInTheDocument()
    expect(screen.getByText(/3, 1 vértices/)).toBeInTheDocument()
  })

  it('C-37: deve exibir as badges de verificação quando houver verificação', () => {
    // Arrange
    const result = criarResultado('kruskal')

    // Act
    render(ResultPanel, { props: { result, verification: verificacao, names: nomes } })

    // Assert
    expect(screen.getByText('✔ estrutura válida')).toBeInTheDocument()
    expect(screen.getByText('✔ propriedade do ciclo')).toBeInTheDocument()
    expect(screen.getByText('✔ custo consistente')).toBeInTheDocument()
  })
})
