const numberFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 3,
  minimumFractionDigits: 3,
})

const integerFormatter = new Intl.NumberFormat('pt-BR')

const percentFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export function formatKm(value: number): string {
  return `${numberFormatter.format(value)} km`
}

export function formatMs(value: number): string {
  if (!Number.isFinite(value)) return '—'
  if (value < 1) return `${value.toFixed(3)} ms`
  return `${value.toFixed(2)} ms`
}

export function formatInteger(value: number): string {
  return integerFormatter.format(value)
}

export function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return `${percentFormatter.format(value * 100)}%`
}
