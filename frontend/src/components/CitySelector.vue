<script setup lang="ts">
import { computed, ref } from 'vue'
import type { City } from '../types'
import { normalizeText } from '../lib/text'

const props = defineProps<{
  cities: City[]
  modelValue: string[]
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: string[]): void
}>()

const search = ref('')
const cityById = computed(() => new Map(props.cities.map((city) => [city.id, city])))
const selectedSet = computed(() => new Set(props.modelValue))

const filtered = computed(() => {
  const query = normalizeText(search.value)
  const list = query
    ? props.cities.filter(
        (city) => normalizeText(city.name).includes(query) || city.id.includes(search.value.trim())
      )
    : props.cities
  return list.slice(0, 160)
})

const selectedCities = computed(() =>
  props.modelValue
    .map((id) => cityById.value.get(id))
    .filter((city): city is City => city !== undefined)
)

function toggle(cityId: string): void {
  const next = new Set(props.modelValue)
  if (next.has(cityId)) next.delete(cityId)
  else next.add(cityId)
  emit('update:modelValue', [...next])
}

function remove(cityId: string): void {
  emit(
    'update:modelValue',
    props.modelValue.filter((id) => id !== cityId)
  )
}

function addNeighbors(): void {
  const next = new Set(props.modelValue)
  for (const cityId of props.modelValue) {
    const city = cityById.value.get(cityId)
    for (const neighbor of city?.neighbors ?? []) next.add(neighbor)
  }
  emit('update:modelValue', [...next])
}

function clear(): void {
  emit('update:modelValue', [])
}
</script>

<template>
  <div class="city-selector">
    <div class="field">
      <label for="city-search">Buscar município por nome ou código IBGE</label>
      <input
        id="city-search"
        v-model="search"
        type="search"
        placeholder="Ex.: Bauru, Ilhabela ou 3506003"
        autocomplete="off"
      />
    </div>

    <div class="selection-summary">
      <strong>{{ modelValue.length }} selecionado(s)</strong>
      <div class="inline-actions">
        <button
          type="button"
          class="link-button"
          :disabled="modelValue.length === 0"
          @click="addNeighbors"
        >
          Adicionar vizinhos
        </button>
        <button
          type="button"
          class="link-button"
          :disabled="modelValue.length === 0"
          @click="clear"
        >
          Limpar
        </button>
      </div>
    </div>

    <ul v-if="selectedCities.length" class="selected-chips" aria-label="Municípios selecionados">
      <li v-for="city in selectedCities" :key="city.id">
        <button type="button" :aria-label="`Remover ${city.name}`" @click="remove(city.id)">
          {{ city.name }} <span aria-hidden="true">×</span>
        </button>
      </li>
    </ul>

    <ul class="city-list" aria-label="Lista de municípios">
      <li v-for="city in filtered" :key="city.id">
        <label class="city-option">
          <input type="checkbox" :checked="selectedSet.has(city.id)" @change="toggle(city.id)" />
          <span class="city-name">{{ city.name }}</span>
          <span class="muted small">{{ city.id }}</span>
          <span class="muted small">{{ city.neighbors.length }} viz.</span>
        </label>
      </li>
    </ul>
    <p v-if="filtered.length === 0" class="muted small">Nenhum município encontrado.</p>
    <p v-else-if="filtered.length === 160" class="muted small">
      Mostrando os 160 primeiros resultados. Refine a busca para encontrar outros.
    </p>
  </div>
</template>
