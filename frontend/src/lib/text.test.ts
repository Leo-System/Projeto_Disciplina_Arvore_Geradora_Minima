import { describe, expect, it } from 'vitest'
import { edgeKey, normalizeText } from './text'

describe('text', () => {
  it('deve remover acentos, caixa, hífen e espaços nas pontas ao normalizar', () => {
    // Arrange
    const value = '  São-Sebastião '

    // Act
    const result = normalizeText(value)

    // Assert
    expect(result).toBe('sao sebastiao')
  })

  it('deve produzir a mesma chave para um par de aresta em qualquer ordem', () => {
    // Arrange
    const direta = { u: 'A', v: 'B' }
    const inversa = { u: 'B', v: 'A' }

    // Act
    const chaveDireta = edgeKey(direta)
    const chaveInversa = edgeKey(inversa)

    // Assert
    expect(chaveDireta).toBe('A|B')
    expect(chaveInversa).toBe('A|B')
  })
})
