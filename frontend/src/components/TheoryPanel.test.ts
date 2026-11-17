import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import TheoryPanel from './TheoryPanel.vue'

describe('TheoryPanel', () => {
  it('C-57: deve cobrir os conceitos teóricos do material', () => {
    // Arrange / Act
    const { container } = render(TheoryPanel)
    const texto = container.textContent ?? ''

    // Assert: conceitos obrigatórios
    for (const conceito of [
      'árvore geradora',
      'acíclico',
      'n − 1',
      'mínima',
      'única',
      'empatados',
      'negativos',
      'Propriedade do corte',
      'Propriedade do ciclo',
      'guloso',
      'Kruskal',
      'Union-Find',
      'Prim',
      'heap',
      'fronteira',
      'O(E log E)',
      'O(E log V)',
      'O(V²)',
      'esparsos',
      'densos',
      'floresta',
      'caminho mais curto',
      'Dijkstra',
    ]) {
      expect(texto).toContain(conceito)
    }
  })

  it('C-58: deve apresentar O(V²) como variante teórica, não como funcionalidade implementada', () => {
    // Arrange / Act
    const { container } = render(TheoryPanel)
    const texto = container.textContent ?? ''

    // Assert
    expect(texto).toContain('Usando heap binário')
    expect(texto).toContain('A variante com vetor e busca linear custa O(V²)')
    expect(texto).not.toMatch(/implementad[oa][^.]*O\(V²\)/i)
  })
})
