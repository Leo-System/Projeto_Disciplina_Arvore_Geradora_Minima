<script setup lang="ts">
import type { Comparison, MstResult } from '../types'
import { formatKm, formatMs } from '../lib/format'
import MetricsTable from './MetricsTable.vue'

defineProps<{
  kruskal: MstResult | null
  prim: MstResult | null
  comparison: Comparison | null
  names: Record<string, string>
}>()

function nameOf(id: string, names: Record<string, string>): string {
  return names[id] || id
}

// BUG-018: diferenças residuais de ponto flutuante (ex.: 3.6e-12) não devem
// aparecer como "0,000 km", o que sugere igualdade exata.
function formatCostDifference(diff: number | null): string {
  if (diff === null) return '—'
  if (Math.abs(diff) < 1e-6 || Math.round(diff * 1000) === 0) return '< 0,001 km'
  return formatKm(diff)
}
</script>

<template>
  <div v-if="!comparison || (!kruskal && !prim)" class="empty-state">
    <h3>Comparação indisponível</h3>
    <p>
      Execute os dois algoritmos (opção <strong>Ambos</strong>) para comparar custo, arestas e
      tempo.
    </p>
  </div>

  <div v-else class="comparison-panel">
    <div class="comparison-cards">
      <section v-if="kruskal" class="algorithm-card">
        <h3>Kruskal</h3>
        <p class="algorithm-cost">{{ formatKm(kruskal.total_cost) }}</p>
        <p class="muted">
          {{ kruskal.edges.length }} arestas · {{ formatMs(kruskal.metrics.time_ms) }}
        </p>
        <MetricsTable :metrics="kruskal.metrics" algorithm="kruskal" />
      </section>
      <section v-if="prim" class="algorithm-card">
        <h3>Prim</h3>
        <p class="algorithm-cost">{{ formatKm(prim.total_cost) }}</p>
        <p class="muted">{{ prim.edges.length }} arestas · {{ formatMs(prim.metrics.time_ms) }}</p>
        <MetricsTable :metrics="prim.metrics" algorithm="prim" />
      </section>
    </div>

    <div class="comparison-message" :class="comparison.is_consistent === false ? 'danger' : 'ok'">
      {{ comparison.message }}
    </div>

    <dl class="comparison-facts">
      <div>
        <dt>Mesmo custo?</dt>
        <dd>{{ comparison.same_cost === null ? '—' : comparison.same_cost ? 'Sim' : 'Não' }}</dd>
      </div>
      <div>
        <dt>Mesmo conjunto de arestas?</dt>
        <dd>{{ comparison.same_edges === null ? '—' : comparison.same_edges ? 'Sim' : 'Não' }}</dd>
      </div>
      <div>
        <dt>Há empates de peso?</dt>
        <dd>
          {{
            comparison.has_weight_ties === null ? '—' : comparison.has_weight_ties ? 'Sim' : 'Não'
          }}
        </dd>
      </div>
      <div>
        <dt>Diferença de custo</dt>
        <dd>{{ formatCostDifference(comparison.cost_difference) }}</dd>
      </div>
    </dl>

    <template v-if="comparison.kruskal_only_edges.length || comparison.prim_only_edges.length">
      <section>
        <h3>Arestas que diferem</h3>
        <div class="diff-grid">
          <div>
            <h4>Só em Kruskal</h4>
            <ul class="edge-list">
              <li v-for="edge in comparison.kruskal_only_edges" :key="`${edge.u}-${edge.v}`">
                {{ nameOf(edge.u, names) }} — {{ nameOf(edge.v, names) }}
                <span class="muted">({{ formatKm(edge.weight) }})</span>
              </li>
            </ul>
            <p v-if="!comparison.kruskal_only_edges.length" class="muted small">Nenhuma.</p>
          </div>
          <div>
            <h4>Só em Prim</h4>
            <ul class="edge-list">
              <li v-for="edge in comparison.prim_only_edges" :key="`${edge.u}-${edge.v}`">
                {{ nameOf(edge.u, names) }} — {{ nameOf(edge.v, names) }}
                <span class="muted">({{ formatKm(edge.weight) }})</span>
              </li>
            </ul>
            <p v-if="!comparison.prim_only_edges.length" class="muted small">Nenhuma.</p>
          </div>
        </div>
      </section>
    </template>

    <section class="complexity-box">
      <h3>Complexidades teóricas</h3>
      <table class="data-table compact">
        <thead>
          <tr>
            <th scope="col">Algoritmo</th>
            <th scope="col">Tempo</th>
            <th scope="col">Estrutura principal</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Kruskal</th>
            <td>O(E log E) = O(E log V)</td>
            <td>ordenação + Union-Find</td>
          </tr>
          <tr>
            <th scope="row">Prim (heap)</th>
            <td>O(E log V)</td>
            <td>fila de prioridade + lista de adjacência</td>
          </tr>
          <tr>
            <th scope="row">Prim (vetor) <span class="theoretical-only">(teórico)</span></th>
            <td>O(V²)</td>
            <td>busca linear da fronteira</td>
          </tr>
        </tbody>
      </table>
      <p class="muted small">
        Kruskal tende a se destacar em grafos esparsos; Prim com vetor tende a se destacar em grafos
        densos. Os tempos medidos aparecem nas tabelas acima.
      </p>
    </section>
  </div>
</template>
