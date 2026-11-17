import type { Edge, TraceEvent } from '../types'

export interface TraceCounters {
  examined: number
  accepted: number
  rejected: number
  skipped: number
  pushes: number
  pops: number
}

export interface TraceSnapshot {
  index: number
  eventsLength: number
  event: TraceEvent | null
  currentEdge: Edge | null
  acceptedEdges: Edge[]
  counters: TraceCounters
  explanation: string
  pseudoLine: number
  progress: number
}

function label(id: string, names: Record<string, string>): string {
  const name = names[id]
  return name && name !== id ? name : id
}

function edgeLabel(edge: { u: string; v: string }, names: Record<string, string>): string {
  return `${label(edge.u, names)} — ${label(edge.v, names)}`
}

function weight(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: 3,
    minimumFractionDigits: 3,
  }).format(value)
}

export function explainEvent(event: TraceEvent | null, names: Record<string, string>): string {
  if (!event) {
    return 'Use os controles para percorrer a execução. O rastro mostra cada decisão tomada pelo algoritmo.'
  }

  switch (event.type) {
    case 'consider': {
      const edge = event.edge
      if (!edge) return 'Analisando a próxima aresta.'
      const sizes = `componentes de tamanho ${event.component_u_size} e ${event.component_v_size}`
      return event.same_component
        ? `Analisando ${edgeLabel(edge, names)} (peso ${weight(edge.weight)}). Os extremos já estão no mesmo componente (${sizes}); aceitar fecharia um ciclo.`
        : `Analisando ${edgeLabel(edge, names)} (peso ${weight(edge.weight)}). Os extremos estão em componentes diferentes (${sizes}), então a aresta é candidata a entrar na árvore.`
    }
    case 'accept': {
      const edge = event.edge
      if (!edge) return 'Aresta aceita.'
      if (event.new_vertex) {
        return `Aceita: ${edgeLabel(edge, names)} (peso ${weight(edge.weight)}) é a aresta mais leve da fronteira e liga ${label(event.from_vertex ?? edge.u, names)} ao novo vértice ${label(event.new_vertex, names)}. Pela propriedade do corte, ela pertence a alguma MST. A árvore tem ${event.tree_size} vértices; ${event.cut_size} ainda estão fora.`
      }
      return `Aceita: ${edgeLabel(edge, names)} (peso ${weight(edge.weight)}). Era a aresta mais leve ainda não analisada que liga dois componentes diferentes. Pela propriedade do corte/ciclo, é segura. Custo parcial: ${weight(event.total_cost_so_far ?? 0)}.`
    }
    case 'reject': {
      const edge = event.edge
      return edge
        ? `Rejeitada: ${edgeLabel(edge, names)} (peso ${weight(edge.weight)}) tem os dois extremos no mesmo componente. Aceitá-la fecharia um ciclo; pela propriedade do ciclo, ela pode ser descartada.`
        : 'Aresta rejeitada por formar ciclo.'
    }
    case 'start':
      return `Prim começa no vértice ${label(event.vertex ?? '', names)}. A árvore inicial tem apenas esse vértice; as arestas incidentes entram na fronteira.`
    case 'restart':
      return `O heap esvaziou e ainda há vértices não visitados. Como o grafo é desconexo, Prim reinicia no vértice ${label(event.vertex ?? '', names)} para construir outra árvore da floresta (componente ${event.component_index}).`
    case 'push': {
      const count = event.edges?.length ?? 0
      return `${count} aresta(s) a partir de ${label(event.vertex ?? '', names)} entraram na fronteira. O heap agora tem ${event.heap_size} entrada(s).`
    }
    case 'pop': {
      const edge = event.edge
      return edge
        ? `EXTRAI-MÍNIMO: a aresta mais leve da fronteira é ${edgeLabel(edge, names)} (peso ${weight(edge.weight)}).`
        : 'EXTRAI-MÍNIMO: retirando a aresta mais leve da fronteira.'
    }
    case 'skip': {
      const edge = event.edge
      return edge
        ? `Entrada obsoleta: ${edgeLabel(edge, names)} é descartada porque o destino já entrou na árvore por outra aresta mais leve.`
        : 'Entrada obsoleta descartada.'
    }
    default:
      return 'Evento de execução.'
  }
}

export function pseudoLineFor(algorithm: 'kruskal' | 'prim', event: TraceEvent | null): number {
  if (!event) return 0
  if (algorithm === 'kruskal') {
    if (event.type === 'accept') return 6
    if (event.type === 'consider' || event.type === 'reject') return 5
    return 0
  }
  switch (event.type) {
    case 'start':
    case 'restart':
      return 2
    case 'push':
      return 7
    case 'pop':
      return 4
    case 'accept':
      return 8
    case 'skip':
      return 4
    default:
      return 0
  }
}

export function buildTraceSnapshot(
  events: TraceEvent[],
  index: number,
  names: Record<string, string>,
  algorithm: 'kruskal' | 'prim'
): TraceSnapshot {
  const safeIndex = Math.max(0, Math.min(index, events.length))
  const counters: TraceCounters = {
    examined: 0,
    accepted: 0,
    rejected: 0,
    skipped: 0,
    pushes: 0,
    pops: 0,
  }
  const acceptedEdges: Edge[] = []

  for (let position = 0; position < safeIndex; position += 1) {
    const event = events[position]
    switch (event.type) {
      case 'consider':
        counters.examined += 1
        break
      case 'accept':
        counters.accepted += 1
        if (event.edge) acceptedEdges.push(event.edge)
        break
      case 'reject':
        counters.rejected += 1
        break
      case 'pop':
        counters.pops += 1
        if (algorithm === 'prim') counters.examined += 1
        break
      case 'skip':
        counters.skipped += 1
        break
      case 'push':
        counters.pushes += event.edges?.length ?? 0
        break
      default:
        break
    }
  }

  const currentEvent = safeIndex > 0 ? events[safeIndex - 1] : null
  return {
    index: safeIndex,
    eventsLength: events.length,
    event: currentEvent,
    currentEdge: currentEvent?.edge ?? null,
    acceptedEdges,
    counters,
    explanation: explainEvent(currentEvent, names),
    pseudoLine: pseudoLineFor(algorithm, currentEvent),
    progress: events.length === 0 ? 0 : safeIndex / events.length,
  }
}
