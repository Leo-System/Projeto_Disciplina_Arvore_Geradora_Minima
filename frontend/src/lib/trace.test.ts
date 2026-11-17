import { describe, expect, it } from 'vitest'
import type { Edge, TraceEvent } from '../types'
import { buildTraceSnapshot, explainEvent, pseudoLineFor } from './trace'

const names = { A: 'Alfa', B: 'Beta' }

function aresta(u: string, v: string, weight: number): Edge {
  return { u, v, weight, attrs: {} }
}

const eventos: TraceEvent[] = [
  {
    type: 'consider',
    edge: aresta('A', 'B', 1),
    component_u_size: 1,
    component_v_size: 1,
    same_component: false,
  },
  { type: 'accept', edge: aresta('A', 'B', 1), total_cost_so_far: 1, accepted_count: 1 },
  {
    type: 'consider',
    edge: aresta('B', 'A', 2),
    component_u_size: 2,
    component_v_size: 2,
    same_component: true,
  },
  { type: 'reject', edge: aresta('B', 'A', 2), reason: 'ciclo' },
]

describe('trace', () => {
  it('deve explicar todos os tipos de evento em português', () => {
    // Arrange
    const casos: TraceEvent[] = [
      {
        type: 'consider',
        edge: aresta('A', 'B', 1),
        component_u_size: 1,
        component_v_size: 1,
        same_component: false,
      },
      { type: 'accept', edge: aresta('A', 'B', 1), total_cost_so_far: 1, accepted_count: 1 },
      { type: 'reject', edge: aresta('A', 'B', 1) },
      { type: 'start', vertex: 'A' },
      { type: 'restart', vertex: 'B', component_index: 2 },
      { type: 'push', vertex: 'A', edges: [aresta('A', 'B', 1)], heap_size: 1 },
      { type: 'pop', edge: aresta('A', 'B', 1) },
      { type: 'skip', edge: aresta('A', 'B', 1) },
    ]

    // Act
    const textos = casos.map((evento) => explainEvent(evento, names))

    // Assert
    expect(textos[0]).toContain('Analisando')
    expect(textos[1]).toContain('Aceita')
    expect(textos[2]).toContain('Rejeitada')
    expect(textos[3]).toContain('Prim começa')
    expect(textos[4]).toContain('reinicia')
    expect(textos[5]).toContain('fronteira')
    expect(textos[6]).toContain('EXTRAI-MÍNIMO')
    expect(textos[7]).toContain('obsoleta')
    expect(explainEvent(null, names)).toContain('controles')
  })

  it('deve mapear eventos do Kruskal para a linha correta do pseudocódigo', () => {
    // Arrange
    const aceite: TraceEvent = { type: 'accept', edge: aresta('A', 'B', 1) }
    const consideracao: TraceEvent = {
      type: 'consider',
      edge: aresta('A', 'B', 1),
      same_component: false,
    }
    const rejeicao: TraceEvent = { type: 'reject', edge: aresta('A', 'B', 1) }

    // Act / Assert
    expect(pseudoLineFor('kruskal', aceite)).toBe(6)
    expect(pseudoLineFor('kruskal', consideracao)).toBe(5)
    expect(pseudoLineFor('kruskal', rejeicao)).toBe(5)
  })

  it('deve mapear o aceite do Prim para extração/relaxamento, não para a linha final', () => {
    // Arrange
    const aceite: TraceEvent = {
      type: 'accept',
      edge: aresta('A', 'B', 1),
      from_vertex: 'A',
      new_vertex: 'B',
      tree_size: 2,
      cut_size: 1,
    }

    // Act
    const linha = pseudoLineFor('prim', aceite)

    // Assert: BUG-003 — hoje retorna 8 (retorne A); o correto é a extração/relaxamento.
    expect([4, 6]).toContain(linha)
    expect(linha).not.toBe(8)
  })

  it('deve mapear os demais eventos do Prim', () => {
    // Arrange / Act / Assert
    expect(pseudoLineFor('prim', { type: 'start', vertex: 'A' })).toBe(2)
    expect(pseudoLineFor('prim', { type: 'restart', vertex: 'A' })).toBe(2)
    expect(pseudoLineFor('prim', { type: 'push', vertex: 'A', edges: [] })).toBe(7)
    expect(pseudoLineFor('prim', { type: 'pop', edge: aresta('A', 'B', 1) })).toBe(4)
    expect(pseudoLineFor('prim', { type: 'skip', edge: aresta('A', 'B', 1) })).toBe(4)
  })

  it('deve montar snapshot vazio com índice e contadores zerados', () => {
    // Arrange
    const lista: TraceEvent[] = []

    // Act
    const snapshot = buildTraceSnapshot(lista, 0, names, 'kruskal')

    // Assert
    expect(snapshot.index).toBe(0)
    expect(snapshot.eventsLength).toBe(0)
    expect(snapshot.event).toBeNull()
    expect(snapshot.progress).toBe(0)
    expect(snapshot.explanation).toContain('controles')
    expect(snapshot.counters).toEqual({
      examined: 0,
      accepted: 0,
      rejected: 0,
      skipped: 0,
      pushes: 0,
      pops: 0,
    })
  })

  it('deve contar examinadas, aceitas e rejeitadas no meio e no fim', () => {
    // Arrange / Act
    const meio = buildTraceSnapshot(eventos, 2, names, 'kruskal')
    const fim = buildTraceSnapshot(eventos, eventos.length, names, 'kruskal')

    // Assert
    expect(meio.counters.examined).toBe(1)
    expect(meio.counters.accepted).toBe(1)
    expect(meio.counters.rejected).toBe(0)
    expect(fim.counters.examined).toBe(2)
    expect(fim.counters.accepted).toBe(1)
    expect(fim.counters.rejected).toBe(1)
  })

  it('deve limitar o índice entre 0 e o tamanho da lista', () => {
    // Arrange / Act / Assert
    expect(buildTraceSnapshot(eventos, -3, names, 'kruskal').index).toBe(0)
    expect(buildTraceSnapshot(eventos, 99, names, 'kruskal').index).toBe(eventos.length)
  })

  it('deve expor arestas aceitas e a aresta atual', () => {
    // Arrange / Act
    const snapshot = buildTraceSnapshot(eventos, 4, names, 'kruskal')

    // Assert
    expect(snapshot.acceptedEdges).toHaveLength(1)
    expect(snapshot.acceptedEdges[0]).toMatchObject({ u: 'A', v: 'B' })
    expect(snapshot.currentEdge).toMatchObject({ u: 'B', v: 'A' })
  })

  it('deve incrementar examinadas a cada pop do Prim', () => {
    // Arrange
    const lista: TraceEvent[] = [
      { type: 'pop', edge: aresta('A', 'B', 1) },
      { type: 'pop', edge: aresta('B', 'C', 1) },
    ]

    // Act
    const snapshot = buildTraceSnapshot(lista, 2, names, 'prim')

    // Assert
    expect(snapshot.counters.pops).toBe(2)
    expect(snapshot.counters.examined).toBe(2)
  })

  it('deve calcular progresso como índice dividido pelo total sem passar de 1', () => {
    // Arrange / Act
    const meio = buildTraceSnapshot(eventos, 2, names, 'kruskal')
    const fim = buildTraceSnapshot(eventos, eventos.length, names, 'kruskal')

    // Assert
    expect(meio.progress).toBe(0.5)
    expect(fim.progress).toBe(1)
  })
})
