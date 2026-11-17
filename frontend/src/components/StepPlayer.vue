<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { TraceEvent } from '../types'
import type { TraceSnapshot } from '../lib/trace'
import { KRUSKAL_PSEUDOCODE, PRIM_PSEUDOCODE } from '../lib/pseudocode'

const props = defineProps<{
  algorithm: 'kruskal' | 'prim'
  events: TraceEvent[]
  index: number
  snapshot: TraceSnapshot
}>()

const emit = defineEmits<{
  (event: 'update:index', value: number): void
}>()

const playing = ref(false)
const speed = ref(20)
const speeds = [1, 5, 20, 50, 200]
let timer: number | null = null
let accumulator = 0

const pseudocode = computed(() =>
  props.algorithm === 'kruskal' ? KRUSKAL_PSEUDOCODE : PRIM_PSEUDOCODE
)

const eventType = computed(() => props.snapshot.event?.type ?? 'início')

const eventBadgeClass = computed(() => {
  const type = eventType.value
  if (type === 'accept') return 'badge-green'
  if (type === 'reject' || type === 'skip') return 'badge-red'
  if (type === 'consider' || type === 'pop' || type === 'push') return 'badge-blue'
  return 'badge-slate'
})

function clampIndex(value: number): number {
  return Math.max(0, Math.min(value, props.events.length))
}

function setIndex(value: number): void {
  emit('update:index', clampIndex(value))
}

function pause(): void {
  playing.value = false
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function start(): void {
  if (props.events.length === 0) return
  if (props.index >= props.events.length) setIndex(0)
  playing.value = true
  accumulator = 0
  timer = window.setInterval(() => {
    accumulator += speed.value * 0.05
    const steps = Math.floor(accumulator)
    if (steps <= 0) return
    accumulator -= steps
    const next = clampIndex(props.index + steps)
    setIndex(next)
    if (next >= props.events.length) pause()
  }, 50)
}

function toggle(): void {
  if (playing.value) pause()
  else start()
}

function stepForward(): void {
  pause()
  setIndex(props.index + 1)
}

function stepBack(): void {
  pause()
  setIndex(props.index - 1)
}

function reset(): void {
  pause()
  setIndex(0)
}

function handleSlider(event: Event): void {
  pause()
  setIndex(Number((event.target as HTMLInputElement).value))
}

watch(
  () => props.algorithm,
  () => pause()
)

watch(
  () => props.events,
  () => pause()
)

onBeforeUnmount(() => pause())
</script>

<template>
  <section class="step-player" aria-label="Modo passo a passo">
    <header class="step-header">
      <div>
        <h3>Passo a passo — {{ algorithm === 'kruskal' ? 'Kruskal' : 'Prim' }}</h3>
        <p class="muted small">
          Evento {{ snapshot.index }} de {{ snapshot.eventsLength }} ·
          {{ Math.round(snapshot.progress * 100) }}% da execução
        </p>
      </div>
      <span class="badge" :class="eventBadgeClass">{{ eventType }}</span>
    </header>

    <div class="step-controls">
      <button
        type="button"
        class="icon-button"
        title="Reiniciar"
        aria-label="Reiniciar animação"
        @click="reset"
      >
        ⏮
      </button>
      <button
        type="button"
        class="icon-button"
        title="Passo anterior"
        aria-label="Passo anterior"
        :disabled="index === 0"
        @click="stepBack"
      >
        ◀
      </button>
      <button type="button" class="primary-button" @click="toggle">
        {{ playing ? 'Pausar' : 'Reproduzir' }}
      </button>
      <button
        type="button"
        class="icon-button"
        title="Próximo passo"
        aria-label="Próximo passo"
        :disabled="index >= events.length"
        @click="stepForward"
      >
        ▶
      </button>
      <label class="speed-control">
        <span class="small">Velocidade</span>
        <select v-model.number="speed" aria-label="Velocidade da animação">
          <option v-for="option in speeds" :key="option" :value="option">
            {{ option }} evento(s)/s
          </option>
        </select>
      </label>
    </div>

    <input
      class="progress-slider"
      type="range"
      min="0"
      :max="events.length"
      :value="index"
      aria-label="Posição na animação"
      @input="handleSlider"
    />

    <div class="step-grid">
      <div>
        <p class="step-explanation" aria-live="polite">{{ snapshot.explanation }}</p>

        <dl class="step-counters">
          <div>
            <dt>Examinadas</dt>
            <dd>{{ snapshot.counters.examined }}</dd>
          </div>
          <div>
            <dt>Aceitas</dt>
            <dd>{{ snapshot.counters.accepted }}</dd>
          </div>
          <div v-if="algorithm === 'kruskal'">
            <dt>Rejeitadas</dt>
            <dd>{{ snapshot.counters.rejected }}</dd>
          </div>
          <template v-else>
            <div>
              <dt>Descartadas</dt>
              <dd>{{ snapshot.counters.skipped }}</dd>
            </div>
            <div>
              <dt>Inserções</dt>
              <dd>{{ snapshot.counters.pushes }}</dd>
            </div>
            <div>
              <dt>Extrações</dt>
              <dd>{{ snapshot.counters.pops }}</dd>
            </div>
          </template>
        </dl>
      </div>

      <div class="pseudocode-block">
        <h4>Pseudocódigo</h4>
        <ol class="pseudocode">
          <li
            v-for="(line, lineIndex) in pseudocode"
            :key="lineIndex"
            :class="{ active: snapshot.pseudoLine === lineIndex + 1 }"
          >
            <code>{{ line }}</code>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>
