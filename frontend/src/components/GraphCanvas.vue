<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Edge, GraphData } from '../types'
import { colorForComponent } from '../lib/graph'
import { computeBasePositions, toScreen, type Point } from '../lib/layout'
import { edgeKey } from '../lib/text'

const props = defineProps<{
  graph: GraphData | null
  mstEdges?: Edge[]
  traceEdges?: Edge[] | null
  currentEdge?: Edge | null
  componentColors?: Record<string, number> | null
  startVertex?: string | null
  showManual: boolean
  showShortBorders: boolean
}>()

const emit = defineEmits<{
  (event: 'select-start', nodeId: string): void
}>()

const container = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const width = ref(800)
const height = ref(520)
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const hoveredId = ref<string | null>(null)
const tooltip = ref<{ x: number; y: number } | null>(null)

let resizeObserver: ResizeObserver | null = null
let dragState: {
  startX: number
  startY: number
  panX: number
  panY: number
  moved: boolean
} | null = null

const basePositions = computed<Map<string, Point>>(() =>
  props.graph ? computeBasePositions(props.graph) : new Map()
)

const degree = computed<Record<string, number>>(() => {
  const degrees: Record<string, number> = {}
  for (const node of props.graph?.nodes ?? []) degrees[node.id] = 0
  for (const edge of props.graph?.edges ?? []) {
    degrees[edge.u] = (degrees[edge.u] ?? 0) + 1
    degrees[edge.v] = (degrees[edge.v] ?? 0) + 1
  }
  return degrees
})

const hoveredNode = computed(() => {
  if (!hoveredId.value || !props.graph) return null
  return props.graph.nodes.find((node) => node.id === hoveredId.value) ?? null
})

const activeEdges = computed<Edge[]>(() => props.traceEdges ?? props.mstEdges ?? [])

function screenOf(nodeId: string): Point | null {
  const base = basePositions.value.get(nodeId)
  if (!base) return null
  return toScreen(base, width.value, height.value, zoom.value, panX.value, panY.value)
}

function draw(): void {
  const element = canvas.value
  const wrapper = container.value
  if (!element || !wrapper) return
  const context = element.getContext('2d')
  if (!context) return

  const dpr = window.devicePixelRatio || 1
  const cssWidth = wrapper.clientWidth
  const cssHeight = wrapper.clientHeight
  if (cssWidth === 0 || cssHeight === 0) return
  if (width.value !== cssWidth || height.value !== cssHeight) {
    width.value = cssWidth
    height.value = cssHeight
  }
  element.width = Math.round(cssWidth * dpr)
  element.height = Math.round(cssHeight * dpr)
  element.style.width = `${cssWidth}px`
  element.style.height = `${cssHeight}px`
  context.setTransform(dpr, 0, 0, dpr, 0, 0)
  context.clearRect(0, 0, cssWidth, cssHeight)

  const graph = props.graph
  if (!graph) {
    context.fillStyle = '#64748b'
    context.font = '16px system-ui, sans-serif'
    context.textAlign = 'center'
    context.fillText('Carregue uma instância para visualizar o grafo.', cssWidth / 2, cssHeight / 2)
    return
  }

  const positions = new Map<string, Point>()
  for (const node of graph.nodes) {
    const screen = screenOf(node.id)
    if (screen) positions.set(node.id, screen)
  }

  const mstSet = new Set(activeEdges.value.map(edgeKey))
  const currentKey = props.currentEdge ? edgeKey(props.currentEdge) : null
  const manyEdges = graph.edges.length > 900
  const baseLine = manyEdges ? 0.8 : 1.2

  const visibleEdges = graph.edges.filter((edge) => {
    const source = String(edge.attrs?.source ?? '')
    if (!props.showManual && source === 'manual') return false
    if (!props.showShortBorders && edge.attrs?.short_border) return false
    return true
  })

  // Primeira passada: arestas comuns.
  context.lineCap = 'round'
  for (const edge of visibleEdges) {
    const key = edgeKey(edge)
    if (mstSet.has(key) || key === currentKey) continue
    const a = positions.get(edge.u)
    const b = positions.get(edge.v)
    if (!a || !b) continue
    const manual = String(edge.attrs?.source ?? '') === 'manual'
    context.beginPath()
    context.strokeStyle = manual ? 'rgba(180, 83, 9, 0.65)' : 'rgba(100, 116, 139, 0.28)'
    context.lineWidth = manual ? 1.4 : baseLine
    context.setLineDash(manual ? [5, 4] : [])
    context.moveTo(a.x, a.y)
    context.lineTo(b.x, b.y)
    context.stroke()
  }

  // Segunda passada: arestas da MST (ou do prefixo animado).
  context.setLineDash([])
  for (const edge of visibleEdges) {
    const key = edgeKey(edge)
    if (!mstSet.has(key) || key === currentKey) continue
    const a = positions.get(edge.u)
    const b = positions.get(edge.v)
    if (!a || !b) continue
    context.beginPath()
    context.strokeStyle = '#0f766e'
    context.lineWidth = manyEdges ? 2 : 2.6
    context.moveTo(a.x, a.y)
    context.lineTo(b.x, b.y)
    context.stroke()
  }

  // Terceira passada: aresta atual do passo a passo.
  if (props.currentEdge) {
    const a = positions.get(props.currentEdge.u)
    const b = positions.get(props.currentEdge.v)
    if (a && b) {
      context.beginPath()
      context.strokeStyle = '#ea580c'
      context.lineWidth = 4
      context.moveTo(a.x, a.y)
      context.lineTo(b.x, b.y)
      context.stroke()
    }
  }

  // Vértices.
  const nodeCount = graph.nodes.length
  const radius = nodeCount > 400 ? 2.5 : nodeCount > 120 ? 3.2 : nodeCount > 30 ? 4.2 : 6
  const showAllLabels = nodeCount <= 30

  for (const node of graph.nodes) {
    const screen = positions.get(node.id)
    if (!screen) continue
    const colorIndex = props.componentColors?.[node.id]
    const fill = colorIndex === undefined ? '#64748b' : colorForComponent(colorIndex)
    const isHovered = hoveredId.value === node.id
    const isStart = props.startVertex === node.id

    context.beginPath()
    context.fillStyle = fill
    context.arc(screen.x, screen.y, isHovered ? radius + 2 : radius, 0, Math.PI * 2)
    context.fill()

    if (isStart) {
      context.beginPath()
      context.strokeStyle = '#ea580c'
      context.lineWidth = 2.4
      context.arc(screen.x, screen.y, radius + 4, 0, Math.PI * 2)
      context.stroke()
    }
    if (isHovered) {
      context.beginPath()
      context.strokeStyle = '#ffffff'
      context.lineWidth = 2
      context.arc(screen.x, screen.y, radius + 2, 0, Math.PI * 2)
      context.stroke()
    }

    if (showAllLabels || isHovered || isStart) {
      const label = node.name?.trim() || node.id
      context.font = '11px system-ui, sans-serif'
      const textWidth = context.measureText(label).width
      const labelX = screen.x + radius + 5
      const labelY = screen.y - radius - 2
      context.fillStyle = 'rgba(255, 255, 255, 0.88)'
      context.fillRect(labelX - 2, labelY - 10, textWidth + 4, 13)
      context.fillStyle = '#0f172a'
      context.textAlign = 'left'
      context.fillText(label, labelX, labelY)
    }
  }
}

function findNodeAt(x: number, y: number): string | null {
  if (!props.graph) return null
  let best: { id: string; distance: number } | null = null
  for (const node of props.graph.nodes) {
    const screen = screenOf(node.id)
    if (!screen) continue
    const distance = Math.hypot(screen.x - x, screen.y - y)
    if (distance <= 11 && (!best || distance < best.distance)) {
      best = { id: node.id, distance }
    }
  }
  return best?.id ?? null
}

function handlePointerDown(event: PointerEvent): void {
  const element = canvas.value
  if (!element) return
  element.setPointerCapture(event.pointerId)
  dragState = {
    startX: event.clientX,
    startY: event.clientY,
    panX: panX.value,
    panY: panY.value,
    moved: false,
  }
}

function handlePointerMove(event: PointerEvent): void {
  const rect = canvas.value?.getBoundingClientRect()
  if (!rect) return
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  if (dragState) {
    const deltaX = event.clientX - dragState.startX
    const deltaY = event.clientY - dragState.startY
    if (Math.hypot(deltaX, deltaY) > 3) dragState.moved = true
    if (dragState.moved) {
      panX.value = dragState.panX + deltaX
      panY.value = dragState.panY + deltaY
      draw()
      return
    }
  }

  const nodeId = findNodeAt(x, y)
  if (nodeId !== hoveredId.value) {
    hoveredId.value = nodeId
    draw()
  }
  tooltip.value = nodeId ? { x, y } : null
}

function handlePointerUp(event: PointerEvent): void {
  const element = canvas.value
  const rect = element?.getBoundingClientRect()
  const wasDrag = dragState?.moved ?? false
  dragState = null
  if (element?.hasPointerCapture(event.pointerId)) {
    element.releasePointerCapture(event.pointerId)
  }
  if (!wasDrag && rect) {
    const nodeId = findNodeAt(event.clientX - rect.left, event.clientY - rect.top)
    if (nodeId) emit('select-start', nodeId)
  }
}

function handlePointerLeave(): void {
  hoveredId.value = null
  tooltip.value = null
  draw()
}

function handleWheel(event: WheelEvent): void {
  event.preventDefault()
  const rect = canvas.value?.getBoundingClientRect()
  if (!rect) return
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const oldZoom = zoom.value
  const newZoom = Math.min(12, Math.max(0.45, oldZoom * Math.exp(-event.deltaY * 0.0014)))
  const size = Math.max(80, Math.min(width.value, height.value) - 68)
  const centerX = width.value / 2
  const centerY = height.value / 2
  const baseX = (x - centerX - panX.value) / (oldZoom * size) + 0.5
  const baseY = (y - centerY - panY.value) / (oldZoom * size) + 0.5
  panX.value = x - centerX - (baseX - 0.5) * size * newZoom
  panY.value = y - centerY - (baseY - 0.5) * size * newZoom
  zoom.value = newZoom
  draw()
}

function zoomBy(factor: number): void {
  zoom.value = Math.min(12, Math.max(0.45, zoom.value * factor))
  draw()
}

function resetView(): void {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
  draw()
}

defineExpose({ resetView })

watch(
  () => [
    props.graph,
    props.mstEdges,
    props.traceEdges,
    props.currentEdge,
    props.componentColors,
    props.startVertex,
    props.showManual,
    props.showShortBorders,
  ],
  () => draw(),
  { deep: false }
)

onMounted(() => {
  if (container.value) {
    resizeObserver = new ResizeObserver(() => draw())
    resizeObserver.observe(container.value)
  }
  draw()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})
</script>

<template>
  <div ref="container" class="graph-canvas-wrap">
    <canvas
      ref="canvas"
      class="graph-canvas"
      role="img"
      aria-label="Grafo dos municípios. Arraste para mover, use a roda do mouse para ampliar e clique em um vértice para defini-lo como início do Prim."
      @pointerdown="handlePointerDown"
      @pointermove="handlePointerMove"
      @pointerup="handlePointerUp"
      @pointerleave="handlePointerLeave"
      @wheel="handleWheel"
      @dblclick="resetView"
    />

    <div
      v-if="hoveredNode && tooltip"
      class="canvas-tooltip"
      :style="{ left: `${tooltip.x + 14}px`, top: `${tooltip.y + 14}px` }"
    >
      <strong>{{ hoveredNode.name || hoveredNode.id }}</strong>
      <span>{{ hoveredNode.id }} · grau {{ degree[hoveredNode.id] ?? 0 }}</span>
    </div>

    <div class="canvas-controls" aria-label="Controles de visualização">
      <button type="button" title="Ampliar" aria-label="Ampliar" @click="zoomBy(1.25)">+</button>
      <button type="button" title="Reduzir" aria-label="Reduzir" @click="zoomBy(0.8)">−</button>
      <button
        type="button"
        title="Restaurar visualização"
        aria-label="Restaurar visualização"
        @click="resetView"
      >
        ⤢
      </button>
    </div>

    <ul class="canvas-legend" aria-label="Legenda do grafo">
      <li><span class="swatch mst" /> Aresta da MST</li>
      <li><span class="swatch manual" /> Ligação manual (balsa)</li>
      <li><span class="swatch current" /> Aresta do passo atual</li>
    </ul>
  </div>
</template>
