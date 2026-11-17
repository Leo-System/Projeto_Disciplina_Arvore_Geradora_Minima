<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api, ApiError } from '../api/client'
import type { BenchmarkResponse, GraphData } from '../types'
import { formatInteger, formatMs } from '../lib/format'
import BenchmarkChart from './BenchmarkChart.vue'

const props = defineProps<{
  graph: GraphData | null
  graphLabel?: string
}>()

const runs = ref(20)
const loading = ref(false)
const error = ref('')
const errorDetails = ref<string[]>([])
const data = ref<BenchmarkResponse | null>(null)

// Ordena as rows por número de vértices (crescente) para que o gráfico de eixo X
// logarítmico e a tabela exibam uma curva ordenada, independentemente da ordem
// em que o backend retornou as medições (ex.: grafo denso com poucos nós mas
// muitas arestas pode vir depois de grafos maiores).
const sortedRows = computed(() => {
  return (data.value?.rows ?? []).slice().sort((a, b) => a.n_nodes - b.n_nodes)
})

// A última linha é sempre o grafo completo: é dela que saem os totais exibidos
// no cabeçalho da medição.
const totals = computed(() => {
  const rows = sortedRows.value
  if (rows.length === 0) return null
  const last = rows[rows.length - 1]
  return { nodes: last.n_nodes, edges: last.n_edges }
})

// Uma medição pertence ao grafo que estava carregado quando foi executada.
// Trocar de instância invalida a tabela anterior.
watch(
  () => props.graph,
  () => {
    data.value = null
    error.value = ''
    errorDetails.value = []
  }
)

async function run(): Promise<void> {
  if (loading.value) return
  const n = Number(runs.value)
  const base = Number.isFinite(n) ? n : 20
  const safeRuns = Math.max(1, Math.min(100, Math.round(base)))
  runs.value = safeRuns
  loading.value = true
  error.value = ''
  errorDetails.value = []
  try {
    data.value = await api.benchmark({
      graph: props.graph,
      runs: safeRuns,
    })
  } catch (caught) {
    if (caught instanceof ApiError) {
      error.value = caught.message
      errorDetails.value = caught.details
    } else {
      error.value = 'Não foi possível executar o benchmark.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="benchmark-panel">
    <header class="benchmark-header">
      <div>
        <h3>Benchmark de Kruskal × Prim</h3>
        <p class="muted">
          Mede o tempo de Kruskal e Prim no grafo carregado. O servidor monta subgrafos induzidos
          crescentes, adicionando vértices em ordem de vizinhança (BFS: primeiro um vértice, depois
          seus vizinhos e assim por diante), em faixas calculadas para gerar cerca de 12 medições
          até o grafo completo. Em cada faixa, os algoritmos rodam várias vezes sem passo a passo,
          após um aquecimento descartado; a tabela mostra a mediana e a faixa p25–p75.
        </p>
      </div>
      <div class="benchmark-controls">
        <label class="field inline-field">
          <span>Execuções por tamanho</span>
          <input v-model.number="runs" type="number" min="1" max="100" step="1" />
        </label>
        <button type="button" class="primary-button" :disabled="loading" @click="run">
          {{ loading ? 'Medindo…' : 'Executar benchmark' }}
        </button>
      </div>
    </header>

    <p class="benchmark-note">
      Os tempos dependem da máquina e do aquecimento do interpretador Python. Compare as curvas
      entre si, não os valores absolutos com outro computador. O limite é de 100 execuções por
      tamanho.
    </p>

    <div v-if="error" class="error-banner" role="alert">
      <strong>{{ error }}</strong>
      <ul v-if="errorDetails.length" class="error-list">
        <li v-for="(detail, index) in errorDetails" :key="index">{{ detail }}</li>
      </ul>
    </div>

    <div v-if="loading" class="empty-state">
      <h3>Medindo tempos…</h3>
      <p>
        O benchmark executa cada algoritmo várias vezes em subgrafos crescentes do grafo atual, até
        o grafo completo.
      </p>
    </div>

    <div v-else-if="!data" class="empty-state">
      <h3>Nenhuma medição ainda</h3>
      <p>
        Clique em <strong>Executar benchmark</strong> para comparar o crescimento do tempo de
        Kruskal e Prim no grafo carregado. As medições são feitas em subgrafos crescentes, a cada
        faixa de vértices, até o grafo completo.
      </p>
    </div>

    <template v-else>
      <p v-if="totals" class="benchmark-meta">
        <strong>{{ graphLabel || data.meta.preset_name }}</strong><template
          v-if="data.meta.start_city_name"
        >
          · início em {{ data.meta.start_city_name }} ({{ data.meta.start_city }})</template
        >
        · {{ formatInteger(totals.nodes) }} vértices · {{ formatInteger(totals.edges) }} arestas ·
        {{ formatInteger(data.meta.runs) }} execução(ões) por tamanho
      </p>

      <BenchmarkChart :rows="sortedRows" />

      <div class="table-scroll">
        <table class="data-table benchmark-table">
          <caption class="sr-only">
            Tempos medianos de Kruskal e Prim por tamanho do subgrafo
          </caption>
          <thead>
            <tr>
              <th scope="col">Vértices</th>
              <th scope="col">Arestas</th>
              <th scope="col">Kruskal — mediana</th>
              <th scope="col">Kruskal — p25–p75</th>
              <th scope="col">Prim — mediana</th>
              <th scope="col">Prim — p25–p75</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedRows" :key="row.n_nodes">
              <td class="numeric">{{ formatInteger(row.n_nodes) }}</td>
              <td class="numeric">{{ formatInteger(row.n_edges) }}</td>
              <td class="numeric">
                <strong>{{ formatMs(row.kruskal_ms) }}</strong>
              </td>
              <td class="numeric muted">
                {{ formatMs(row.kruskal_p25_ms) }} – {{ formatMs(row.kruskal_p75_ms) }}
              </td>
              <td class="numeric">
                <strong>{{ formatMs(row.prim_ms) }}</strong>
              </td>
              <td class="numeric muted">
                {{ formatMs(row.prim_p25_ms) }} – {{ formatMs(row.prim_p75_ms) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="muted small">{{ data.meta.note }}</p>
    </template>
  </section>
</template>
