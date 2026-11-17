<script setup lang="ts">
import type { MstResult, Verification } from '../types'
import { formatKm, formatMs } from '../lib/format'
import MstEdgeTable from './MstEdgeTable.vue'
import MetricsTable from './MetricsTable.vue'
import VerificationBadges from './VerificationBadges.vue'

defineProps<{
  result: MstResult | null
  verification: Verification | null
  names: Record<string, string>
}>()
</script>

<template>
  <div v-if="!result" class="empty-state">
    <h3>Nenhuma execução ainda</h3>
    <p>
      Escolha uma instância (ou monte o seu grafo), defina o algoritmo e clique em
      <strong>Executar</strong>.
    </p>
  </div>

  <div v-else class="result-panel">
    <div class="summary-grid">
      <div class="summary-card">
        <span class="summary-label">Custo total</span>
        <strong>{{ formatKm(result.total_cost) }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">Arestas aceitas</span>
        <strong>{{ result.edges.length }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">Componentes</span>
        <strong>{{ result.n_components }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">Tempo (sem trace)</span>
        <strong>{{ formatMs(result.metrics.time_ms ?? 0) }}</strong>
      </div>
    </div>

    <p v-if="result.n_components > 1" class="notice">
      O grafo é desconexo: o resultado é uma <strong>floresta geradora mínima</strong> com
      {{ result.edges.length }} arestas (n − c). Componentes:
      {{ result.components.map((component) => component.size).join(', ') }} vértices.
    </p>

    <VerificationBadges v-if="verification" :verification="verification" />

    <section>
      <h3>Métricas de {{ result.algorithm === 'kruskal' ? 'Kruskal' : 'Prim' }}</h3>
      <MetricsTable :metrics="result.metrics" :algorithm="result.algorithm" />
    </section>

    <section>
      <h3>Arestas escolhidas</h3>
      <MstEdgeTable :edges="result.edges" :names="names" />
    </section>
  </div>
</template>
