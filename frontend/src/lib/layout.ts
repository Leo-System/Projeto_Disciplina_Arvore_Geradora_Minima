import type { GraphData } from '../types'

export interface Point {
  x: number
  y: number
}

/**
 * Posições base normalizadas em [0,1], preservando o formato geográfico.
 * Grafos sem coordenadas usam um layout circular.
 */
export function computeBasePositions(graph: GraphData): Map<string, Point> {
  const positions = new Map<string, Point>()
  const nodes = graph.nodes
  if (nodes.length === 0) return positions

  const hasCoordinates = nodes.every(
    (node) =>
      typeof node.lat === 'number' &&
      Number.isFinite(node.lat) &&
      typeof node.lon === 'number' &&
      Number.isFinite(node.lon)
  )

  if (hasCoordinates && nodes.length > 1) {
    const meanLat = nodes.reduce((sum, node) => sum + (node.lat as number), 0) / nodes.length
    const cosLat = Math.cos((meanLat * Math.PI) / 180)

    const projected = nodes.map((node) => ({
      id: node.id,
      x: (node.lon as number) * cosLat,
      y: node.lat as number,
    }))

    const minX = Math.min(...projected.map((item) => item.x))
    const maxX = Math.max(...projected.map((item) => item.x))
    const minY = Math.min(...projected.map((item) => item.y))
    const maxY = Math.max(...projected.map((item) => item.y))
    const span = Math.max(maxX - minX, maxY - minY) || 1
    const padX = (1 - (maxX - minX) / span) / 2
    const padY = (1 - (maxY - minY) / span) / 2

    for (const item of projected) {
      positions.set(item.id, {
        x: padX + (item.x - minX) / span,
        // Latitude cresce para o norte; no canvas o y cresce para baixo.
        y: padY + (maxY - item.y) / span,
      })
    }
    return positions
  }

  if (nodes.length === 1) {
    positions.set(nodes[0].id, { x: 0.5, y: 0.5 })
    return positions
  }

  nodes.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / nodes.length - Math.PI / 2
    positions.set(node.id, {
      x: 0.5 + 0.42 * Math.cos(angle),
      y: 0.5 + 0.42 * Math.sin(angle),
    })
  })
  return positions
}

export function toScreen(
  point: Point,
  width: number,
  height: number,
  zoom: number,
  panX: number,
  panY: number,
  padding = 34
): Point {
  const size = Math.max(80, Math.min(width, height) - 2 * padding)
  return {
    x: width / 2 + (point.x - 0.5) * size * zoom + panX,
    y: height / 2 + (point.y - 0.5) * size * zoom + panY,
  }
}
