<script setup lang="ts">
import { computed } from 'vue'
import { formatMs } from '../lib/format'

const props = defineProps<{
  metrics: Record<string, number>
  algorithm: 'kruskal' | 'prim'
}>()

const labels: Record<string, string> = {
  time_ms: 'Tempo (sem trace)',
  edges_examined: 'Arestas examinadas',
  accepted: 'Arestas aceitas',
  rejected: 'Arestas rejeitadas',
  find_calls: 'Chamadas a find',
  union_calls: 'Chamadas a union',
  heap_pushes: 'Inserções no heap',
  heap_pops: 'Extrações do heap',
  stale_pops: 'Entradas obsoletas',
}

const order =
  props.algorithm === 'kruskal'
    ? ['time_ms', 'edges_examined', 'accepted', 'rejected', 'find_calls', 'union_calls']
    : ['time_ms', 'edges_examined', 'accepted', 'heap_pushes', 'heap_pops', 'stale_pops']

const rows = computed(() =>
  order
    .filter((key) => key in props.metrics)
    .map((key) => ({
      key,
      label: labels[key] ?? key,
      value: key === 'time_ms' ? formatMs(props.metrics[key]) : String(props.metrics[key]),
    }))
)
</script>

<template>
  <table class="data-table compact">
    <caption class="sr-only">
      Métricas da execução
    </caption>
    <tbody>
      <tr v-for="row in rows" :key="row.key">
        <th scope="row">{{ row.label }}</th>
        <td class="numeric">{{ row.value }}</td>
      </tr>
    </tbody>
  </table>
</template>
