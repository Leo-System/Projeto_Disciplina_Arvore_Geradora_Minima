import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import ModelingPanel from './ModelingPanel.vue'

describe('ModelingPanel', () => {
  it('C-59: deve apresentar a modelagem e as seis hipóteses/limitações', () => {
    // Arrange / Act
    const { container } = render(ModelingPanel)
    const texto = container.textContent ?? ''

    // Assert: modelagem
    for (const termo of [
      'Modelagem do grafo',
      'Vértices',
      'Arestas',
      'código IBGE de 7 dígitos',
      'Tipo',
      'Não direcionado',
      'ponderado',
      'simples',
      'Peso',
      'Haversine',
      '6.371,0088 km',
      'border_km',
      'source',
      'short_border',
    ]) {
      expect(texto).toContain(termo)
    }

    // Assert: 6 limitações
    expect(screen.getByRole('heading', { name: 'Hipóteses e limitações' })).toBeInTheDocument()
    expect(container.querySelectorAll('.limitations-list > li')).toHaveLength(6)
    expect(texto).toContain('linha reta entre sedes')
    expect(texto).toContain('subgrafo induzido')
    expect(texto).toContain('floresta geradora mínima')
    expect(texto).toContain('Biritiba Mirim')
  })
})
