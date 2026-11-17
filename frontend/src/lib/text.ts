export function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/-/g, ' ')
    .trim()
}

export function edgeKey(edge: { u: string; v: string }): string {
  return edge.u <= edge.v ? `${edge.u}|${edge.v}` : `${edge.v}|${edge.u}`
}
