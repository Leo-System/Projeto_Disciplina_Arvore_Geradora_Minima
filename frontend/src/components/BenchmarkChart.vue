<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { BenchmarkRow } from '../types'
import { formatInteger, formatMs } from '../lib/format'

const props = defineProps<{
  rows: BenchmarkRow[]
}>()

const wrapper = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const width = ref(720)
const height = ref(340)
const hover = ref<{
  x: number
  y: number
  row: BenchmarkRow
  series: 'kruskal' | 'prim'
} | null>(null)

interface PlotPoint {
  x: number
  y: number
  row: BenchmarkRow
  series: 'kruskal' | 'prim'
}

let points: PlotPoint[] = []
let resizeObserver: ResizeObserver | null = null

const KRUSKAL_COLOR = '#0f766e'
const PRIM_COLOR = '#7c3aed'

function niceCeil(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1
  const exponent = Math.floor(Math.log10(value))
  const base = 10 ** exponent
  const fraction = value / base
  let nice = 1
  if (fraction > 5) nice = 10
  else if (fraction > 2) nice = 5
  else if (fraction > 1) nice = 2
  return nice * base
}

function tickLabel(value: number, maxValue: number): string {
  if (maxValue >= 10) return value.toFixed(0)
  if (maxValue >= 1) return value.toFixed(1)
  return value.toFixed(2)
}

function draw(): void {
  const element = canvas.value
  const container = wrapper.value
  if (!element || !container) return
  const context = element.getContext('2d')
  if (!context) return

  const dpr = window.devicePixelRatio || 1
  const cssWidth = container.clientWidth
  const cssHeight = container.clientHeight
  if (cssWidth === 0 || cssHeight === 0) return

  width.value = cssWidth
  height.value = cssHeight
  element.width = Math.round(cssWidth * dpr)
  element.height = Math.round(cssHeight * dpr)
  element.style.width = `${cssWidth}px`
  element.style.height = `${cssHeight}px`
  context.setTransform(dpr, 0, 0, dpr, 0, 0)
  context.clearRect(0, 0, cssWidth, cssHeight)
  points = []

  context.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif'
  context.textBaseline = 'middle'

  if (props.rows.length === 0) {
    context.fillStyle = '#64748b'
    context.textAlign = 'center'
    context.font = '14px system-ui, -apple-system, "Segoe UI", sans-serif'
    context.fillText('Sem dados de benchmark.', cssWidth / 2, cssHeight / 2)
    return
  }

  const pad = { top: 34, right: 24, bottom: 48, left: 68 }
  const innerWidth = Math.max(40, cssWidth - pad.left - pad.right)
  const innerHeight = Math.max(40, cssHeight - pad.top - pad.bottom)

  const nodeCounts = props.rows.map((row) => row.n_nodes)
  const minNodes = Math.min(...nodeCounts)
  const maxNodes = Math.max(...nodeCounts)
  const logMin = Math.log10(minNodes)
  const logMax = Math.log10(maxNodes)

  const xFor = (value: number): number => {
    if (logMax === logMin) return pad.left + innerWidth / 2
    const ratio = (Math.log10(value) - logMin) / (logMax - logMin)
    return pad.left + ratio * innerWidth
  }

  const rawMax = Math.max(
    0.001,
    ...props.rows.flatMap((row) => [
      row.kruskal_ms,
      row.kruskal_p75_ms,
      row.prim_ms,
      row.prim_p75_ms,
    ])
  )
  const yMax = niceCeil(rawMax * 1.12)
  const yFor = (value: number): number => pad.top + innerHeight - (value / yMax) * innerHeight

  // Grade horizontal e eixo Y.
  context.textAlign = 'right'
  context.fillStyle = '#64748b'
  for (let index = 0; index <= 4; index += 1) {
    const value = (yMax / 4) * index
    const y = yFor(value)
    context.beginPath()
    context.strokeStyle = index === 0 ? 'rgba(100, 116, 139, 0.45)' : 'rgba(100, 116, 139, 0.16)'
    context.lineWidth = 1
    context.moveTo(pad.left, y)
    context.lineTo(pad.left + innerWidth, y)
    context.stroke()
    context.fillText(tickLabel(value, yMax), pad.left - 10, y)
  }

  // Título do eixo Y.
  context.save()
  context.translate(16, pad.top + innerHeight / 2)
  context.rotate(-Math.PI / 2)
  context.textAlign = 'center'
  context.fillStyle = '#475569'
  context.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif'
  context.fillText('tempo (ms)', 0, 0)
  context.restore()

  // Eixo X e rótulos de tamanho.
  context.textAlign = 'center'
  context.textBaseline = 'top'
  context.fillStyle = '#64748b'
  let lastLabelX = -Infinity
  const labelSlots: number[] = []
  for (const row of props.rows) {
    const x = xFor(row.n_nodes)
    if (x - lastLabelX >= 46 || labelSlots.length === 0) {
      labelSlots.push(x)
      lastLabelX = x
    }
  }
  for (const row of props.rows) {
    const x = xFor(row.n_nodes)
    if (!labelSlots.some((slot) => Math.abs(slot - x) < 0.5)) continue
    context.fillText(formatInteger(row.n_nodes), x, pad.top + innerHeight + 12)
  }
  context.fillStyle = '#475569'
  context.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif'
  context.fillText(
    'vértices (escala logarítmica)',
    pad.left + innerWidth / 2,
    pad.top + innerHeight + 31
  )

  // Faixas p25–p75.
  for (const row of props.rows) {
    const x = xFor(row.n_nodes)
    const bands: Array<[number, number, string]> = [
      [row.kruskal_p25_ms, row.kruskal_p75_ms, KRUSKAL_COLOR],
      [row.prim_p25_ms, row.prim_p75_ms, PRIM_COLOR],
    ]
    for (const [low, high, color] of bands) {
      context.beginPath()
      context.strokeStyle = `${color}55`
      context.lineWidth = 7
      context.lineCap = 'round'
      context.moveTo(x, yFor(low))
      context.lineTo(x, yFor(high))
      context.stroke()
    }
  }

  // Linhas das medianas.
  const series: Array<{
    key: 'kruskal' | 'prim'
    color: string
    value: (row: BenchmarkRow) => number
  }> = [
    { key: 'kruskal', color: KRUSKAL_COLOR, value: (row) => row.kruskal_ms },
    { key: 'prim', color: PRIM_COLOR, value: (row) => row.prim_ms },
  ]

  for (const item of series) {
    context.beginPath()
    context.strokeStyle = item.color
    context.lineWidth = 2.2
    context.lineJoin = 'round'
    props.rows.forEach((row, index) => {
      const x = xFor(row.n_nodes)
      const y = yFor(item.value(row))
      if (index === 0) context.moveTo(x, y)
      else context.lineTo(x, y)
    })
    context.stroke()

    for (const row of props.rows) {
      const x = xFor(row.n_nodes)
      const y = yFor(item.value(row))
      points.push({ x, y, row, series: item.key })

      const highlighted = hover.value?.row === row && hover.value?.series === item.key
      context.beginPath()
      context.fillStyle = '#ffffff'
      context.arc(x, y, highlighted ? 6 : 4, 0, Math.PI * 2)
      context.fill()
      context.beginPath()
      context.fillStyle = item.color
      context.arc(x, y, highlighted ? 4 : 2.6, 0, Math.PI * 2)
      context.fill()
      if (highlighted) {
        context.beginPath()
        context.strokeStyle = item.color
        context.lineWidth = 2
        context.arc(x, y, 8, 0, Math.PI * 2)
        context.stroke()
      }
    }
  }

  // Legenda.
  const legendY = 16
  let legendX = pad.left
  context.textBaseline = 'middle'
  context.textAlign = 'left'
  context.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif'
  for (const item of series) {
    context.beginPath()
    context.strokeStyle = item.color
    context.lineWidth = 2.5
    context.moveTo(legendX, legendY)
    context.lineTo(legendX + 22, legendY)
    context.stroke()
    context.beginPath()
    context.fillStyle = item.color
    context.arc(legendX + 11, legendY, 3.5, 0, Math.PI * 2)
    context.fill()
    context.fillStyle = '#334155'
    context.fillText(item.key === 'kruskal' ? 'Kruskal' : 'Prim', legendX + 29, legendY)
    legendX += 106
  }
  context.fillStyle = '#94a3b8'
  context.fillText('faixa = p25–p75 · ponto = mediana', legendX + 4, legendY)
}

function handleMove(event: MouseEvent): void {
  const rect = canvas.value?.getBoundingClientRect()
  if (!rect) return
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  let nearest: PlotPoint | null = null
  let bestDistance = 22
  for (const point of points) {
    const distance = Math.hypot(point.x - x, point.y - y)
    if (distance < bestDistance) {
      bestDistance = distance
      nearest = point
    }
  }
  const next = nearest
    ? { x: nearest.x, y: nearest.y, row: nearest.row, series: nearest.series }
    : null
  const changed = next?.row !== hover.value?.row || next?.series !== hover.value?.series
  hover.value = next
  if (changed) draw()
}

function handleLeave(): void {
  if (hover.value) {
    hover.value = null
    draw()
  }
}

function tooltipStyle(): Record<string, string> {
  if (!hover.value) return {}
  const left = Math.min(Math.max(hover.value.x + 14, 8), width.value - 230)
  const top = Math.max(hover.value.y - 12, 8)
  return { left: `${left}px`, top: `${top}px` }
}

watch(
  () => props.rows,
  () => {
    hover.value = null
    draw()
  },
  { deep: true }
)

onMounted(() => {
  if (wrapper.value) {
    resizeObserver = new ResizeObserver(() => draw())
    resizeObserver.observe(wrapper.value)
  }
  draw()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})
</script>

<template>
  <div ref="wrapper" class="benchmark-chart-wrap">
    <canvas
      ref="canvas"
      class="benchmark-chart"
      role="img"
      aria-label="Gráfico de linhas comparando o tempo mediano de Kruskal e Prim por número de vértices. Os valores exatos estão na tabela abaixo."
      @mousemove="handleMove"
      @mouseleave="handleLeave"
    />

    <div v-if="hover" class="chart-tooltip" :style="tooltipStyle()" aria-live="polite">
      <strong
        >{{ formatInteger(hover.row.n_nodes) }} vértices ·
        {{ formatInteger(hover.row.n_edges) }} arestas</strong
      >
      <span>
        <b>{{ hover.series === 'kruskal' ? 'Kruskal' : 'Prim' }}:</b>
        {{ formatMs(hover.series === 'kruskal' ? hover.row.kruskal_ms : hover.row.prim_ms) }}
      </span>
      <span class="muted small">
        p25–p75:
        {{
          formatMs(hover.series === 'kruskal' ? hover.row.kruskal_p25_ms : hover.row.prim_p25_ms)
        }}
        –
        {{
          formatMs(hover.series === 'kruskal' ? hover.row.kruskal_p75_ms : hover.row.prim_p75_ms)
        }}
      </span>
    </div>
  </div>
</template>
