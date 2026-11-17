<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  loading: boolean
}>()

const emit = defineEmits<{
  (event: 'upload', file: File): void
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const dragging = ref(false)

function chooseFile(): void {
  fileInput.value?.click()
}

function setFile(file: File | null): void {
  selectedFile.value = file
}

function handleInput(event: Event): void {
  const input = event.target as HTMLInputElement
  setFile(input.files?.[0] ?? null)
}

function handleDrop(event: DragEvent): void {
  event.preventDefault()
  dragging.value = false
  const file = event.dataTransfer?.files?.[0] ?? null
  if (file) setFile(file)
}

function submit(): void {
  if (selectedFile.value) emit('upload', selectedFile.value)
}
</script>

<template>
  <div class="upload-panel">
    <div
      class="drop-zone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop="handleDrop"
    >
      <p><strong>Arraste um arquivo CSV ou JSON</strong> para cá.</p>
      <p class="muted small">Limite de 5 MB e 200.000 arestas.</p>
      <button type="button" class="secondary-button" @click="chooseFile">Escolher arquivo</button>
      <input
        ref="fileInput"
        class="sr-only"
        type="file"
        accept=".csv,.json,text/csv,application/json"
        @change="handleInput"
      />
    </div>

    <p v-if="selectedFile" class="selected-file">
      <strong>{{ selectedFile.name }}</strong>
      <span class="muted small">({{ Math.ceil(selectedFile.size / 1024) }} KB)</span>
    </p>

    <button
      type="button"
      class="primary-button full-width"
      :disabled="!selectedFile || loading"
      @click="submit"
    >
      {{ loading ? 'Enviando…' : 'Carregar grafo do arquivo' }}
    </button>

    <details class="format-help">
      <summary>Formatos aceitos</summary>
      <p>
        <strong>CSV:</strong> cabeçalho <code>origem,destino,peso</code> (ou
        <code>source,target,weight</code>), separador <code>,</code> ou <code>;</code>.
      </p>
      <pre>
origem,destino,peso
A,B,12.5
B,C,7</pre>
      <p><strong>JSON:</strong> objeto com <code>nodes</code> (opcional) e <code>edges</code>.</p>
      <pre>
{
  "nodes": [{"id": "A", "lat": -22.3, "lon": -49.0}],
  "edges": [{"source": "A", "target": "B", "weight": 12.5}]
}</pre>
      <p class="muted small">Arquivos de exemplo estão na pasta <code>examples/</code>.</p>
    </details>
  </div>
</template>
