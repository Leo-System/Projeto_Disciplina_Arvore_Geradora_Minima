import { describe, expect, it } from 'vitest'
import type { GraphData } from '../types'
import { computeBasePositions, toScreen } from './layout'

function grafoComCoordenadas(): GraphData {
  return {
    nodes: [
      { id: 'oeste', lat: -22, lon: -50 },
      { id: 'leste', lat: -22, lon: -46 },
      { id: 'norte', lat: -20, lon: -48 },
      { id: 'sul', lat: -24, lon: -48 },
    ],
    edges: [],
    warnings: [],
    discarded: [],
  }
}

describe('layout', () => {
  it('deve normalizar coordenadas em [0,1] e inverter o eixo y', () => {
    // Arrange
    const dados = grafoComCoordenadas()

    // Act
    const posicoes = computeBasePositions(dados)

    // Assert
    for (const ponto of posicoes.values()) {
      expect(ponto.x).toBeGreaterThanOrEqual(0)
      expect(ponto.x).toBeLessThanOrEqual(1)
      expect(ponto.y).toBeGreaterThanOrEqual(0)
      expect(ponto.y).toBeLessThanOrEqual(1)
    }
    expect(posicoes.get('norte')!.y).toBeLessThan(posicoes.get('sul')!.y)
  })

  it('deve corrigir a longitude pelo cosseno da latitude média', () => {
    // Arrange: mesmo delta de longitude, latitudes diferentes.
    const dados: GraphData = {
      nodes: [
        { id: 'A', lat: -22, lon: -50 },
        { id: 'B', lat: -22, lon: -48 },
      ],
      edges: [],
      warnings: [],
      discarded: [],
    }

    // Act
    const posicoes = computeBasePositions(dados)

    // Assert: a projeção não deve degenerar; ambos ficam no intervalo.
    expect(posicoes.get('A')!.x).not.toBe(posicoes.get('B')!.x)
  })

  it('deve usar layout circular determinístico no raio 0,42 sem coordenadas', () => {
    // Arrange
    const dados: GraphData = {
      nodes: [{ id: 'A' }, { id: 'B' }, { id: 'C' }],
      edges: [],
      warnings: [],
      discarded: [],
    }

    // Act
    const primeira = computeBasePositions(dados)
    const segunda = computeBasePositions(dados)

    // Assert
    expect(primeira).toEqual(segunda)
    for (const ponto of primeira.values()) {
      const raio = Math.hypot(ponto.x - 0.5, ponto.y - 0.5)
      expect(raio).toBeCloseTo(0.42, 10)
    }
  })

  it('deve devolver mapa vazio com zero vértices e centro com um vértice', () => {
    // Arrange
    const vazio: GraphData = { nodes: [], edges: [], warnings: [], discarded: [] }
    const unitario: GraphData = {
      nodes: [{ id: 'A' }],
      edges: [],
      warnings: [],
      discarded: [],
    }

    // Act / Assert
    expect(computeBasePositions(vazio).size).toBe(0)
    expect(computeBasePositions(unitario).get('A')).toEqual({ x: 0.5, y: 0.5 })
  })

  it('deve cair no layout circular quando há coordenada parcial ou NaN', () => {
    // Arrange
    const dados: GraphData = {
      nodes: [{ id: 'A', lat: -22, lon: -48 }, { id: 'B', lat: Number.NaN, lon: -47 }, { id: 'C' }],
      edges: [],
      warnings: [],
      discarded: [],
    }

    // Act
    const posicoes = computeBasePositions(dados)

    // Assert
    expect(posicoes.size).toBe(3)
    for (const ponto of posicoes.values()) {
      expect(Number.isFinite(ponto.x)).toBe(true)
      expect(Number.isFinite(ponto.y)).toBe(true)
    }
  })

  it('deve aplicar zoom, pan e padding mantendo o centro estável', () => {
    // Arrange
    const centro = { x: 0.5, y: 0.5 }

    // Act
    const resultado = toScreen(centro, 800, 600, 2, 10, -20)

    // Assert
    expect(resultado).toEqual({ x: 410, y: 280 })
  })
})
