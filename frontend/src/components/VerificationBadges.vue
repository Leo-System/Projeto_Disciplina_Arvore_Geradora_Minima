<script setup lang="ts">
import type { Verification } from '../types'

defineProps<{
  verification: Verification
}>()
</script>

<template>
  <div class="verification-block" :class="{ invalid: !verification.is_valid }">
    <div class="badge-row">
      <span class="badge" :class="verification.is_forest ? 'badge-green' : 'badge-red'">
        {{ verification.is_forest ? '✔ estrutura válida' : '✘ estrutura inválida' }}
      </span>
      <span
        v-if="verification.performed"
        class="badge"
        :class="verification.cycle_property ? 'badge-green' : 'badge-red'"
      >
        {{ verification.cycle_property ? '✔ propriedade do ciclo' : '✘ propriedade do ciclo' }}
      </span>
      <span v-else class="badge badge-slate">propriedade do ciclo não verificada</span>
      <span class="badge" :class="verification.cost_consistent ? 'badge-green' : 'badge-red'">
        {{ verification.cost_consistent ? '✔ custo consistente' : '✘ custo inconsistente' }}
      </span>
    </div>
    <p class="verification-message">{{ verification.message }}</p>
    <ul v-if="verification.details.length" class="error-list">
      <li v-for="(detail, index) in verification.details.slice(0, 8)" :key="index">{{ detail }}</li>
    </ul>
  </div>
</template>
