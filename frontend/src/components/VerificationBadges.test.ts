import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import VerificationBadges from './VerificationBadges.vue'
import { verificacao } from '../test/fixtures'
import type { Verification } from '../types'

describe('VerificationBadges', () => {
  it('C-46: deve exibir estados válidos e detalhes limitados a 8', () => {
    // Arrange
    const verification: Verification = {
      ...verificacao,
      details: Array.from({ length: 10 }, (_, indice) => `detalhe ${indice}`),
    }

    // Act
    render(VerificationBadges, { props: { verification } })

    // Assert
    expect(screen.getByText('✔ estrutura válida')).toBeInTheDocument()
    expect(screen.getByText('✔ propriedade do ciclo')).toBeInTheDocument()
    expect(screen.getByText('✔ custo consistente')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(8)
  })

  it('C-46: deve exibir estados inválidos e "não verificada" quando performed=false', () => {
    // Arrange
    const verification: Verification = {
      performed: false,
      is_forest: false,
      cycle_property: false,
      is_valid: false,
      cost_consistent: false,
      message: 'Resultado inválido.',
      details: ['faltam arestas'],
    }

    // Act
    render(VerificationBadges, { props: { verification } })

    // Assert
    expect(screen.getByText('✘ estrutura inválida')).toBeInTheDocument()
    expect(screen.getByText('propriedade do ciclo não verificada')).toBeInTheDocument()
    expect(screen.getByText('✘ custo inconsistente')).toBeInTheDocument()
    expect(screen.getByText('Resultado inválido.')).toBeInTheDocument()
    expect(screen.getByText('faltam arestas')).toBeInTheDocument()
  })
})
