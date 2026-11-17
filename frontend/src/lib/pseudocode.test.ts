import { describe, expect, it } from 'vitest'
import { KRUSKAL_PSEUDOCODE, PRIM_PSEUDOCODE } from './pseudocode'

describe('pseudocode', () => {
  it('deve conter os passos do Kruskal na ordem do material', () => {
    // Arrange / Act
    const linhas = KRUSKAL_PSEUDOCODE

    // Assert
    expect(linhas.length).toBeGreaterThanOrEqual(9)
    expect(linhas[0]).toContain('A ← ∅')
    expect(linhas.join('\n')).toContain('MAKE-SET')
    expect(linhas.join('\n')).toContain('FIND-SET')
    expect(linhas.join('\n')).toContain('UNION')
    expect(linhas.join('\n')).toContain('|A| = |V| − 1')
  })

  it('deve conter os passos do Prim com chave, pai e fila de prioridade', () => {
    // Arrange / Act
    const linhas = PRIM_PSEUDOCODE

    // Assert
    expect(linhas.length).toBeGreaterThanOrEqual(8)
    expect(linhas.join('\n')).toContain('chave[v]')
    expect(linhas.join('\n')).toContain('pai[v]')
    expect(linhas.join('\n')).toContain('EXTRAI-MÍNIMO')
    expect(linhas.join('\n')).toContain('retorne A')
  })
})
