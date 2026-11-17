<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Edge } from '../types'
import { formatKm } from '../lib/format'

const props = defineProps<{
  edges: Edge[]
  names: Record<string, string>
}>()

const showAll = ref(false)
const visibleEdges = computed(() => (showAll.value ? props.edges : props.edges.slice(0, 120)))

function nameOf(id: string): string {
  return props.names[id] || id
}
</script>

<template>
  <div class="edge-table-block">
    <p v-if="edges.length === 0" class="muted">Nenhuma aresta foi aceita.</p>
    <template v-else>
      <div class="table-scroll">
        <table class="data-table">
          <caption class="sr-only">
            Arestas escolhidas pela árvore geradora mínima
          </caption>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Município A</th>
              <th scope="col">Município B</th>
              <th scope="col">Distância</th>
              <th scope="col">Origem</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(edge, index) in visibleEdges" :key="`${edge.u}-${edge.v}`">
              <td>{{ index + 1 }}</td>
              <td>
                {{ nameOf(edge.u) }} <span class="muted small">({{ edge.u }})</span>
              </td>
              <td>
                {{ nameOf(edge.v) }} <span class="muted small">({{ edge.v }})</span>
              </td>
              <td class="numeric">{{ formatKm(edge.weight) }}</td>
              <td>
                <span v-if="edge.attrs?.source === 'manual'" class="badge badge-orange"
                  >manual</span
                >
                <span v-else class="badge badge-slate">divisa</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <button
        v-if="edges.length > 120"
        type="button"
        class="link-button"
        @click="showAll = !showAll"
      >
        {{
          showAll ? 'Mostrar apenas as 120 primeiras' : `Mostrar todas as ${edges.length} arestas`
        }}
      </button>
    </template>
  </div>
</template>
