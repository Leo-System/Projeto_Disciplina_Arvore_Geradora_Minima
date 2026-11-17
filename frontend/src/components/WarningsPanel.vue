<script setup lang="ts">
import type { DiscardedCity } from '../types'

defineProps<{
  warnings: string[]
  discarded: DiscardedCity[]
}>()
</script>

<template>
  <section v-if="warnings.length || discarded.length" class="warnings-block" aria-live="polite">
    <h3>Avisos</h3>
    <ul class="warning-list">
      <li v-for="(warning, index) in warnings" :key="index">{{ warning }}</li>
    </ul>
    <template v-if="discarded.length">
      <h4>Vértices descartados</h4>
      <ul class="warning-list discarded">
        <li v-for="city in discarded" :key="city.id">
          <strong>{{ city.name }}</strong> ({{ city.id }}): {{ city.reason }}
        </li>
      </ul>
    </template>
  </section>
</template>
