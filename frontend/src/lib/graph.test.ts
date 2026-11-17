import { describe, expect, it } from 'vitest'
import type { Edge, GraphData } from '../types'
import {
  COMPONENT_PALETTE,
  colorForComponent,
  componentColorMap,
  componentsFromResult,
  degreeMap,
  edgeSet,
  nodeNameMap,
} from './graph'

function edge(u: string, v: string, weight = 1): Edge {
  return { u, v, weight, attrs: {} }
}

function grafo(ids: string[], arestas: Edge[]): GraphData {
  return {
    nodes: ids.map((id) => ({ id, name: id, lat: null, lon: null })),
    edges: arestas,
    warnings: [],
    discarded: [],
  }
}

describe('graph', () => {
  it('deve agrupar vértices conectados no mesmo componente', () => {
    // Arrange
    const ids = ['A', 'B', 'C', 'D']
    const arestas = [edge('A', 'B'), edge('C', 'D')]

    // Act
    const mapa = componentColorMap(ids, arestas)

    // Assert
    expect(mapa.A).toBe(mapa.B)
    expect(mapa.C).toBe(mapa.D)
    expect(mapa.A).not.toBe(mapa.C)
  })

  it('deve excluir vértices isolados quando onlyConnected é verdadeiro', () => {
    // Arrange
    const ids = ['A', 'B', 'Z']
    const arestas = [edge('A', 'B')]

    // Act
    const mapa = componentColorMap(ids, arestas, true)

    // Assert
    expect(mapa).toHaveProperty('A')
    expect(mapa).toHaveProperty('B')
    expect(mapa).not.toHaveProperty('Z')
  })

  it('deve considerar extraNodes ao marcar vértices tocados', () => {
    // Arrange
    const ids = ['A', 'B', 'Z']
    const arestas = [edge('A', 'B')]

    // Act
    const mapa = componentColorMap(ids, arestas, true, ['Z'])

    // Assert
    expect(mapa).toHaveProperty('Z')
  })

  it('deve calcular o grau incluindo vértices isolados com grau zero', () => {
    // Arrange
    const dados = grafo(['A', 'B', 'Z'], [edge('A', 'B')])

    // Act
    const graus = degreeMap(dados)

    // Assert
    expect(graus).toEqual({ A: 1, B: 1, Z: 0 })
  })

  it('deve usar o nome e cair para o id quando o nome é vazio ou ausente', () => {
    // Arrange
    const dados: GraphData = {
      nodes: [{ id: '1', name: 'Bauru' }, { id: '2', name: '   ' }, { id: '3' }],
      edges: [],
      warnings: [],
      discarded: [],
    }

    // Act
    const nomes = nodeNameMap(dados)

    // Assert
    expect(nomes).toEqual({ '1': 'Bauru', '2': '2', '3': '3' })
  })

  it('deve aceitar null e undefined em edgeSet e remover duplicatas', () => {
    // Arrange
    const arestas = [edge('A', 'B'), edge('B', 'A')]

    // Act / Assert
    expect(edgeSet(null).size).toBe(0)
    expect(edgeSet(undefined).size).toBe(0)
    expect(edgeSet(arestas).size).toBe(1)
  })

  it('deve mapear node_ids para o índice do componente', () => {
    // Arrange
    const componentes = [
      { size: 2, node_ids: ['A', 'B'] },
      { size: 1, node_ids: ['C'] },
    ]

    // Act
    const mapa = componentsFromResult(componentes)

    // Assert
    expect(mapa).toEqual({ A: 0, B: 0, C: 1 })
  })

  it('deve percorrer a paleta de forma cíclica sem devolver undefined', () => {
    // Arrange
    const index = COMPONENT_PALETTE.length + 2

    // Act
    const cor = colorForComponent(index)

    // Assert
    expect(cor).toBe(COMPONENT_PALETTE[2])
    expect(cor).toBeDefined()
  })
})
