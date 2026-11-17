import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import WarningsPanel from './WarningsPanel.vue'

describe('WarningsPanel', () => {
  it('C-47: deve ocultar o painel quando não há avisos nem descartados', () => {
    // Arrange / Act
    const { container } = render(WarningsPanel, { props: { warnings: [], discarded: [] } })

    // Assert
    expect(container.querySelector('.warnings-block')).toBeNull()
  })

  it('C-47: deve listar avisos e vértices descartados', () => {
    // Arrange
    const warnings = ['Grafo desconexo: 2 componentes.', 'Aviso adicional.']
    const discarded = [{ id: '3520400', name: 'Ilhabela', reason: 'sem divisa no componente' }]

    // Act
    render(WarningsPanel, { props: { warnings, discarded } })

    // Assert
    expect(screen.getByRole('heading', { name: 'Avisos' })).toBeInTheDocument()
    expect(screen.getByText('Grafo desconexo: 2 componentes.')).toBeInTheDocument()
    expect(screen.getByText('Aviso adicional.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vértices descartados' })).toBeInTheDocument()
    expect(screen.getByText(/Ilhabela/)).toBeInTheDocument()
    expect(screen.getByText(/3520400/)).toBeInTheDocument()
    expect(screen.getByText(/sem divisa no componente/)).toBeInTheDocument()
  })
})
