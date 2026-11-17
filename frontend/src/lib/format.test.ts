import { describe, expect, it } from 'vitest'
import { formatInteger, formatKm, formatMs, formatPercent } from './format'

describe('format', () => {
  it('deve formatar quilômetros com três casas e separador pt-BR', () => {
    // Arrange
    const value = 1234.5

    // Act
    const result = formatKm(value)

    // Assert
    expect(result).toBe('1.234,500 km')
  })

  it('deve formatar milissegundos abaixo de 1 com três casas', () => {
    // Arrange / Act
    const result = formatMs(0.5)

    // Assert
    expect(result).toBe('0.500 ms')
  })

  it('deve formatar milissegundos a partir de 1 com duas casas', () => {
    // Arrange / Act
    const result = formatMs(12.345)

    // Assert
    expect(result).toBe('12.35 ms')
  })

  it('deve devolver travessão quando o tempo não é finito', () => {
    // Arrange / Act
    const result = formatMs(Number.POSITIVE_INFINITY)

    // Assert
    expect(result).toBe('—')
  })

  it('deve formatar inteiros com separador de milhar pt-BR', () => {
    // Arrange / Act
    const result = formatInteger(1234)

    // Assert
    expect(result).toBe('1.234')
  })

  it('deve formatar percentual com uma casa e separador pt-BR', () => {
    // Arrange / Act
    const result = formatPercent(0.123)

    // Assert
    expect(result).toBe('12,3%')
  })
})
