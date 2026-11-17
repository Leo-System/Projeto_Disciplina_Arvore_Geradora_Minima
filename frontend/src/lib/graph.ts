import type { Edge, GraphData } from '../types'
import { edgeKey } from './text'

/** Componentes conexos da floresta formada por um subconjunto de arestas. */
export function componentColorMap(
  nodeIds: string[],
  edges: Edge[],
  onlyConnected = false,
  extraNodes: string[] = []
): Record<string, number> {
  const parent = new Map<string, string>()
  for (const id of nodeIds) parent.set(id, id)

  const find = (node: string): string => {
    let root = node
    while (parent.get(root) !== root) root = parent.get(root) as string
    let current = node
    while (parent.get(current) !== current) {
      const next = parent.get(current) as string
      parent.set(current, root)
      current = next
    }
    return root
  }

  const union = (a: string, b: string): void => {
    const rootA = find(a)
    const rootB = find(b)
    if (rootA === rootB) return
    parent.set(rootB, rootA)
  }

  const touched = new Set<string>(extraNodes)
  for (const edge of edges) {
    if (!parent.has(edge.u) || !parent.has(edge.v)) continue
    union(edge.u, edge.v)
    touched.add(edge.u)
    touched.add(edge.v)
  }

  const roots = new Map<string, number>()
  const colors: Record<string, number> = {}
  for (const node of nodeIds) {
    const root = find(node)
    if (onlyConnected && !touched.has(node)) continue
    if (!roots.has(root)) roots.set(root, roots.size)
    colors[node] = roots.get(root) as number
  }
  return colors
}

/** Mapa id -> grau no grafo (para a dica do canvas). */
export function degreeMap(graph: GraphData): Record<string, number> {
  const degrees: Record<string, number> = {}
  for (const node of graph.nodes) degrees[node.id] = 0
  for (const edge of graph.edges) {
    degrees[edge.u] = (degrees[edge.u] ?? 0) + 1
    degrees[edge.v] = (degrees[edge.v] ?? 0) + 1
  }
  return degrees
}

export function nodeNameMap(graph: GraphData): Record<string, string> {
  const names: Record<string, string> = {}
  for (const node of graph.nodes) names[node.id] = node.name?.trim() || node.id
  return names
}

export function edgeSet(edges: Edge[] | null | undefined): Set<string> {
  const set = new Set<string>()
  for (const edge of edges ?? []) set.add(edgeKey(edge))
  return set
}

export function componentsFromResult(
  components: { size: number; node_ids: string[] }[]
): Record<string, number> {
  const colors: Record<string, number> = {}
  components.forEach((component, index) => {
    for (const nodeId of component.node_ids) colors[nodeId] = index
  })
  return colors
}

export const COMPONENT_PALETTE = [
  '#0f766e',
  '#7c3aed',
  '#b45309',
  '#be123c',
  '#1d4ed8',
  '#4d7c0f',
  '#a21caf',
  '#0e7490',
  '#9a3412',
  '#4338ca',
  '#15803d',
  '#b91c1c',
]

export function colorForComponent(index: number): string {
  return COMPONENT_PALETTE[index % COMPONENT_PALETTE.length]
}
