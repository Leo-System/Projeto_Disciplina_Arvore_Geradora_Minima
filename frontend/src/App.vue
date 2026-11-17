<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api, ApiError } from './api/client'
import type {
  City,
  GraphData,
  GraphStats,
  MstResult,
  PresetSummary,
  RunResponse,
  TraceEvent,
  Verification,
} from './types'
import { formatInteger } from './lib/format'
import { componentsFromResult, nodeNameMap } from './lib/graph'
import { buildTraceSnapshot } from './lib/trace'
import BenchmarkPanel from './components/BenchmarkPanel.vue'
import CitySelector from './components/CitySelector.vue'
import ComparisonPanel from './components/ComparisonPanel.vue'
import GraphCanvas from './components/GraphCanvas.vue'
import ModelingPanel from './components/ModelingPanel.vue'
import ResultPanel from './components/ResultPanel.vue'
import StepPlayer from './components/StepPlayer.vue'
import TheoryPanel from './components/TheoryPanel.vue'
import UploadPanel from './components/UploadPanel.vue'
import WarningsPanel from './components/WarningsPanel.vue'

type SourceMode = 'preset' | 'cities' | 'upload'
type AlgorithmChoice = 'kruskal' | 'prim' | 'both'
type ResultKey = 'kruskal' | 'prim'
type TabId = 'resultado' | 'comparacao' | 'passo' | 'benchmark' | 'teoria' | 'modelagem'

const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'resultado', label: 'Resultado' },
  { id: 'comparacao', label: 'Comparação' },
  { id: 'passo', label: 'Passo a passo' },
  { id: 'benchmark', label: 'Benchmark' },
  { id: 'teoria', label: 'Teoria' },
  { id: 'modelagem', label: 'Modelagem' },
]

const cities = ref<City[]>([])
const presets = ref<PresetSummary[]>([])
const bootLoading = ref(true)
const graphLoading = ref(false)
const running = ref(false)

const sourceMode = ref<SourceMode>('preset')
const selectedPresetId = ref('p1-bauru-vizinhos')
const selectedCityIds = ref<string[]>([])
const includeManual = ref(true)
const connectComponents = ref(false)

const graph = ref<GraphData | null>(null)
const graphLabel = ref('')
const graphDescription = ref('')

const algorithm = ref<AlgorithmChoice>('both')
const startVertex = ref<string | null>(null)
const traceEnabled = ref(true)
const verifyEnabled = ref(true)

const runResponse = ref<RunResponse | null>(null)
const resultAlgorithm = ref<ResultKey>('kruskal')
const traceAlgorithm = ref<ResultKey>('kruskal')
const traceIndex = ref(0)
const activeTab = ref<TabId>('resultado')

const showManual = ref(true)
const showShortBorders = ref(true)
const canvasRef = ref<{ resetView: () => void } | null>(null)

const errorMessage = ref('')
const errorDetails = ref<string[]>([])
const errorCode = ref('')

let graphRequestToken = 0
let runToken = 0

const names = computed<Record<string, string>>(() => (graph.value ? nodeNameMap(graph.value) : {}))

const nodeOptions = computed(() =>
  graph.value
    ? [...graph.value.nodes].sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id, 'pt-BR'))
    : []
)

const cityCount = computed(() => cities.value.length)

const graphStats = computed<GraphStats | null>(
  () => graph.value?.stats ?? runResponse.value?.graph_stats ?? null
)

const selectedResult = computed<MstResult | null>(() => {
  const response = runResponse.value
  if (!response) return null
  if (response[resultAlgorithm.value]) return response[resultAlgorithm.value]
  if (response.kruskal) return response.kruskal
  return response.prim
})

const selectedVerification = computed<Verification | null>(() => {
  const response = runResponse.value
  if (!response?.verification) return null
  const key = selectedResult.value?.algorithm
  return key ? (response.verification[key] ?? null) : null
})

const hasKruskal = computed(() => Boolean(runResponse.value?.kruskal))
const hasPrim = computed(() => Boolean(runResponse.value?.prim))
const hasBoth = computed(() => hasKruskal.value && hasPrim.value)

const traceEvents = computed<TraceEvent[]>(() => {
  const result = runResponse.value?.[traceAlgorithm.value]
  return result?.trace ?? []
})

const traceSnapshot = computed(() =>
  buildTraceSnapshot(traceEvents.value, traceIndex.value, names.value, traceAlgorithm.value)
)

const displayEdges = computed(() => {
  if (activeTab.value === 'passo' && traceEvents.value.length > 0) {
    return traceSnapshot.value.acceptedEdges
  }
  return selectedResult.value?.edges ?? []
})

const displayCurrentEdge = computed(() =>
  activeTab.value === 'passo' ? traceSnapshot.value.currentEdge : null
)

const componentColors = computed<Record<string, number> | null>(() => {
  const result =
    activeTab.value === 'passo'
      ? (runResponse.value?.[traceAlgorithm.value] ?? null)
      : selectedResult.value
  if (!result || result.n_components <= 1) return null
  return componentsFromResult(result.components)
})

const canExecute = computed(() => Boolean(graph.value) && !running.value && !graphLoading.value)

function describeError(caught: unknown, fallback: string): void {
  if (caught instanceof ApiError) {
    errorMessage.value = caught.message
    errorDetails.value = caught.details
    errorCode.value = caught.code
    return
  }
  errorMessage.value = caught instanceof Error && caught.message ? caught.message : fallback
  errorDetails.value = []
  errorCode.value = ''
}

function clearError(): void {
  errorMessage.value = ''
  errorDetails.value = []
  errorCode.value = ''
}

function applyGraph(next: GraphData, label: string, description: string): void {
  runToken += 1
  graph.value = next
  graphLabel.value = label
  graphDescription.value = description
  runResponse.value = null
  traceIndex.value = 0
  if (startVertex.value && !next.nodes.some((node) => node.id === startVertex.value)) {
    startVertex.value = null
  }
  if (next.nodes.length === 0) startVertex.value = null
}

async function loadPreset(presetId: string, autoRun = true): Promise<void> {
  const token = ++graphRequestToken
  clearError()
  graphLoading.value = true
  let loaded = false
  try {
    const detail = await api.preset(presetId)
    if (token !== graphRequestToken) return
    selectedPresetId.value = presetId
    sourceMode.value = 'preset'
    applyGraph(detail.graph, detail.name, detail.description)
    loaded = true
  } catch (caught) {
    if (token === graphRequestToken) {
      describeError(caught, 'Não foi possível carregar a instância pronta.')
    }
  } finally {
    if (token === graphRequestToken) graphLoading.value = false
  }
  if (loaded && autoRun) await execute()
}

async function buildSelection(): Promise<void> {
  if (selectedCityIds.value.length < 2) {
    errorMessage.value = 'Selecione ao menos 2 municípios para montar o grafo.'
    errorDetails.value = []
    errorCode.value = 'VALIDATION_ERROR'
    return
  }
  clearError()
  graphLoading.value = true
  let loaded = false
  try {
    const connect = connectComponents.value
    const built = await api.buildGraph(
      selectedCityIds.value,
      includeManual.value,
      connect
    )
    applyGraph(
      built,
      connect
        ? `Seleção conectada de ${formatInteger(built.nodes.length)} municípios`
        : `Seleção de ${formatInteger(built.nodes.length)} municípios`,
      connect
        ? 'Subgrafo induzido pela seleção, com municípios adicionados automaticamente por vizinhança até o grafo ficar conexo.'
        : 'Subgrafo induzido pela seleção: entram apenas as divisas com as duas pontas escolhidas.'
    )
    loaded = true
  } catch (caught) {
    describeError(caught, 'Não foi possível montar o grafo a partir da seleção.')
  } finally {
    graphLoading.value = false
  }
  if (loaded) await execute()
}

async function handleUpload(file: File): Promise<void> {
  clearError()
  graphLoading.value = true
  let loaded = false
  try {
    const uploaded = await api.uploadGraph(file)
    applyGraph(
      uploaded,
      file.name,
      'Grafo carregado de arquivo CSV ou JSON. O peso de cada aresta vem da coluna ou campo informado.'
    )
    loaded = true
  } catch (caught) {
    describeError(caught, 'Não foi possível carregar o arquivo enviado.')
  } finally {
    graphLoading.value = false
  }
  if (loaded) await execute()
}

async function execute(): Promise<void> {
  const currentGraph = graph.value
  if (!currentGraph || running.value) return
  clearError()
  running.value = true
  const token = ++runToken
  try {
    const response = await api.run({
      graph: currentGraph,
      algorithm: algorithm.value,
      start_vertex: algorithm.value === 'kruskal' ? null : startVertex.value,
      trace: traceEnabled.value,
      verify: verifyEnabled.value,
    })
    if (token !== runToken || graph.value !== currentGraph) return
    runResponse.value = response

    const preferred: ResultKey = response.kruskal ? 'kruskal' : 'prim'
    resultAlgorithm.value = preferred
    if (response[preferred]?.trace) {
      traceAlgorithm.value = preferred
    } else if (response.kruskal?.trace) {
      traceAlgorithm.value = 'kruskal'
    } else if (response.prim?.trace) {
      traceAlgorithm.value = 'prim'
    }
    traceIndex.value = 0
  } catch (caught) {
    if (token === runToken) {
      describeError(caught, 'Não foi possível executar os algoritmos.')
    }
  } finally {
    if (token === runToken) running.value = false
  }
}

function choosePreset(presetId: string): void {
  if (graphLoading.value) return
  void loadPreset(presetId, true)
}

function chooseSource(mode: SourceMode): void {
  sourceMode.value = mode
  clearError()
}

function chooseAlgorithm(value: AlgorithmChoice): void {
  algorithm.value = value
  if (value === 'kruskal') startVertex.value = null
}

function handleSelectStart(nodeId: string): void {
  startVertex.value = nodeId
  if (algorithm.value === 'kruskal') algorithm.value = 'both'
}

function runWithTrace(): void {
  traceEnabled.value = true
  activeTab.value = 'passo'
  void execute()
}

function selectResultAlgorithm(value: ResultKey): void {
  if (!runResponse.value?.[value]) return
  resultAlgorithm.value = value
}

function selectTraceAlgorithm(value: ResultKey): void {
  if (!runResponse.value?.[value]?.trace) return
  traceAlgorithm.value = value
  traceIndex.value = 0
}

function resetView(): void {
  canvasRef.value?.resetView()
}

watch(traceAlgorithm, () => {
  traceIndex.value = 0
})

watch(traceEvents, () => {
  traceIndex.value = 0
})

onMounted(async () => {
  bootLoading.value = true
  clearError()
  try {
    const [cityList, presetList] = await Promise.all([api.cities(), api.presets()])
    cities.value = cityList
    presets.value = presetList
    const initial =
      presetList.find((preset) => preset.id === selectedPresetId.value) ?? presetList[0]
    if (initial) {
      await loadPreset(initial.id, false)
      await execute()
    }
  } catch (caught) {
    describeError(caught, 'Não foi possível carregar os dados iniciais do sistema.')
  } finally {
    bootLoading.value = false
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">AGM</div>
        <div>
          <h1>Árvore Geradora Mínima</h1>
          <p class="brand-subtitle">
            Malha municipal de São Paulo · Prim e Kruskal implementados do zero
          </p>
        </div>
      </div>
      <div class="header-meta">
        <span v-if="cityCount" class="badge badge-slate">
          {{ formatInteger(cityCount) }} municípios
        </span>
        <a class="link-button" href="/docs" target="_blank" rel="noopener"> Documentação da API </a>
      </div>
    </header>

    <div v-if="errorMessage" class="error-banner" role="alert">
      <div class="error-banner-text">
        <strong>{{ errorMessage }}</strong>
        <span v-if="errorCode" class="muted small">Código: {{ errorCode }}</span>
        <ul v-if="errorDetails.length" class="error-list">
          <li v-for="(detail, index) in errorDetails" :key="index">{{ detail }}</li>
        </ul>
      </div>
      <button
        type="button"
        class="icon-button"
        aria-label="Fechar aviso de erro"
        @click="clearError"
      >
        ×
      </button>
    </div>

    <div v-if="bootLoading" class="loading-strip" role="status">
      <span class="spinner" aria-hidden="true" />
      Carregando municípios, instâncias e o resultado inicial…
    </div>
    <div v-else-if="graphLoading" class="loading-strip" role="status">
      <span class="spinner" aria-hidden="true" />
      Carregando o grafo…
    </div>
    <div v-else-if="running" class="loading-strip" role="status">
      <span class="spinner" aria-hidden="true" />
      Executando
      {{ algorithm === 'both' ? 'Kruskal e Prim' : algorithm === 'kruskal' ? 'Kruskal' : 'Prim' }}…
    </div>

    <div class="app-body">
      <aside class="control-sidebar" aria-label="Configuração da execução">
        <section class="panel">
          <h2><span class="step-number">1</span> Escolha a instância</h2>

          <div class="source-tabs" role="group" aria-label="Fonte do grafo">
            <button
              type="button"
              :class="{ active: sourceMode === 'preset' }"
              :aria-pressed="sourceMode === 'preset'"
              @click="chooseSource('preset')"
            >
              Prontas
            </button>
            <button
              type="button"
              :class="{ active: sourceMode === 'cities' }"
              :aria-pressed="sourceMode === 'cities'"
              @click="chooseSource('cities')"
            >
              Selecionar
            </button>
            <button
              type="button"
              :class="{ active: sourceMode === 'upload' }"
              :aria-pressed="sourceMode === 'upload'"
              @click="chooseSource('upload')"
            >
              Arquivo
            </button>
          </div>

          <div v-if="sourceMode === 'preset'" class="source-body">
            <div v-if="presets.length === 0" class="muted small">Carregando instâncias…</div>
            <ul v-else class="preset-list">
              <li v-for="preset in presets" :key="preset.id">
                <button
                  type="button"
                  class="preset-card"
                  :class="{ active: selectedPresetId === preset.id }"
                  :aria-pressed="selectedPresetId === preset.id"
                  @click="choosePreset(preset.id)"
                >
                  <span class="preset-name">{{ preset.name }}</span>
                  <span class="preset-description">{{ preset.description }}</span>
                  <span class="preset-meta">
                    <span class="badge badge-slate"
                      >{{ formatInteger(preset.n_nodes) }} vértices</span
                    >
                    <span class="badge badge-slate"
                      >{{ formatInteger(preset.n_edges) }} arestas</span
                    >
                    <span v-if="preset.n_components > 1" class="badge badge-orange">
                      {{ preset.n_components }} componentes
                    </span>
                    <span v-if="!preset.include_manual" class="badge badge-slate">
                      sem ligações manuais
                    </span>
                    <span v-else class="badge badge-blue">com balsa</span>
                  </span>
                </button>
              </li>
            </ul>
          </div>

          <div v-else-if="sourceMode === 'cities'" class="source-body">
            <p class="muted small">
              Monte o subgrafo induzido pela sua seleção. Só entram divisas com as duas pontas
              escolhidas.
            </p>
            <CitySelector v-model="selectedCityIds" :cities="cities" />
            <label class="check-row">
              <input v-model="includeManual" type="checkbox" />
              Incluir ligações manuais (balsa Ilhabela–São Sebastião)
            </label>
            <button
              type="button"
              class="primary-button full-width"
              :disabled="selectedCityIds.length < 2 || graphLoading"
              @click="buildSelection"
            >
              {{ graphLoading ? 'Montando…' : `Montar grafo (${selectedCityIds.length})` }}
            </button>
          </div>

          <div v-else class="source-body">
            <UploadPanel :loading="graphLoading" @upload="handleUpload" />
          </div>
        </section>

        <section class="panel">
          <h2><span class="step-number">2</span> Parâmetros</h2>

          <label v-if="sourceMode === 'cities'" class="check-row">
            <input v-model="connectComponents" type="checkbox" />
            Conectar as cidades selecionadas em um único grafo
          </label>
          <p v-if="sourceMode === 'cities'" class="hint">
            Adiciona vizinhos automaticamente até a seleção ficar conexa. Pode incluir muitos
            municípios. A opção é aplicada ao clicar em <strong>Montar grafo</strong>.
          </p>

          <fieldset class="field">
            <legend>Algoritmo</legend>
            <div class="segmented" role="group" aria-label="Algoritmo a executar">
              <button
                type="button"
                :class="{ active: algorithm === 'kruskal' }"
                :aria-pressed="algorithm === 'kruskal'"
                @click="chooseAlgorithm('kruskal')"
              >
                Kruskal
              </button>
              <button
                type="button"
                :class="{ active: algorithm === 'prim' }"
                :aria-pressed="algorithm === 'prim'"
                @click="chooseAlgorithm('prim')"
              >
                Prim
              </button>
              <button
                type="button"
                :class="{ active: algorithm === 'both' }"
                :aria-pressed="algorithm === 'both'"
                @click="chooseAlgorithm('both')"
              >
                Ambos
              </button>
            </div>
          </fieldset>

          <div class="field">
            <label for="start-vertex">Vértice inicial do Prim</label>
            <select
              id="start-vertex"
              v-model="startVertex"
              :disabled="algorithm === 'kruskal' || !graph"
            >
              <option :value="null">Automático (primeiro vértice)</option>
              <option v-for="node in nodeOptions" :key="node.id" :value="node.id">
                {{ node.name || node.id }} — {{ node.id }}
              </option>
            </select>
            <p class="hint">
              Você também pode clicar em um vértice no grafo para defini-lo como início.
            </p>
          </div>

          <label class="check-row">
            <input v-model="traceEnabled" type="checkbox" />
            Gerar passo a passo
          </label>
          <label class="check-row">
            <input v-model="verifyEnabled" type="checkbox" />
            Verificar resultado
          </label>

          <button
            type="button"
            class="primary-button full-width execute-button"
            :disabled="!canExecute"
            @click="execute"
          >
            {{ running ? 'Executando…' : 'Executar algoritmos' }}
          </button>

          <p v-if="graphStats && graphStats.n_nodes === 0" class="hint danger-text">
            Nenhum vértice no grafo atual. Escolha outra instância.
          </p>
        </section>

        <section class="panel">
          <h2><span class="step-number">3</span> Visualização</h2>
          <label class="check-row">
            <input v-model="showManual" type="checkbox" />
            Mostrar ligações manuais
          </label>
          <label class="check-row">
            <input v-model="showShortBorders" type="checkbox" />
            Mostrar divisas com menos de 0,5 km
          </label>
          <button type="button" class="secondary-button full-width" @click="resetView">
            Restaurar enquadramento
          </button>
          <ul class="mini-legend" aria-label="Legenda das cores">
            <li><span class="swatch mst" /> Aresta escolhida</li>
            <li><span class="swatch current" /> Aresta do passo atual</li>
            <li><span class="swatch manual" /> Ligação manual</li>
          </ul>
        </section>
      </aside>

      <main class="workspace">
        <section class="graph-section" aria-label="Visualização do grafo">
          <div class="graph-toolbar">
            <div class="graph-title">
              <h2>{{ graphLabel || 'Nenhuma instância carregada' }}</h2>
              <p v-if="graphDescription" class="muted small">{{ graphDescription }}</p>
            </div>
            <div v-if="graphStats" class="stat-chips">
              <span class="stat-chip">
                <strong>{{ formatInteger(graphStats.n_nodes) }}</strong> vértices
              </span>
              <span class="stat-chip">
                <strong>{{ formatInteger(graphStats.n_edges) }}</strong> arestas
              </span>
              <span class="stat-chip" :class="{ warning: !graphStats.is_connected }">
                <strong>{{ formatInteger(graphStats.n_components) }}</strong>
                {{ graphStats.n_components === 1 ? 'componente' : 'componentes' }}
              </span>
              <span v-if="graphStats.n_manual_edges" class="stat-chip manual">
                <strong>{{ formatInteger(graphStats.n_manual_edges) }}</strong> manual(is)
              </span>
            </div>
          </div>

          <GraphCanvas
            ref="canvasRef"
            :graph="graph"
            :trace-edges="displayEdges"
            :current-edge="displayCurrentEdge"
            :component-colors="componentColors"
            :start-vertex="startVertex"
            :show-manual="showManual"
            :show-short-borders="showShortBorders"
            @select-start="handleSelectStart"
          />

          <WarningsPanel v-if="graph" :warnings="graph.warnings" :discarded="graph.discarded" />
        </section>

        <section class="results-section" aria-label="Resultados e conteúdo">
          <nav class="tab-bar" role="tablist" aria-label="Seções do sistema">
            <button
              v-for="tab in tabs"
              :id="`tab-${tab.id}`"
              :key="tab.id"
              type="button"
              role="tab"
              :aria-selected="activeTab === tab.id"
              :aria-controls="`panel-${tab.id}`"
              :class="{ active: activeTab === tab.id }"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
              <span v-if="tab.id === 'passo' && traceEvents.length" class="tab-count">
                {{ formatInteger(traceEvents.length) }}
              </span>
            </button>
          </nav>

          <section
            v-show="activeTab === 'resultado'"
            id="panel-resultado"
            class="tab-panel"
            role="tabpanel"
            aria-labelledby="tab-resultado"
          >
            <div v-if="hasBoth" class="result-toolbar">
              <span class="muted small">Ver resultado de</span>
              <div class="segmented compact" role="group" aria-label="Resultado exibido">
                <button
                  type="button"
                  :class="{ active: resultAlgorithm === 'kruskal' }"
                  :aria-pressed="resultAlgorithm === 'kruskal'"
                  @click="selectResultAlgorithm('kruskal')"
                >
                  Kruskal
                </button>
                <button
                  type="button"
                  :class="{ active: resultAlgorithm === 'prim' }"
                  :aria-pressed="resultAlgorithm === 'prim'"
                  @click="selectResultAlgorithm('prim')"
                >
                  Prim
                </button>
              </div>
            </div>
            <ResultPanel
              :result="selectedResult"
              :verification="selectedVerification"
              :names="names"
            />
          </section>

          <section
            v-show="activeTab === 'comparacao'"
            id="panel-comparacao"
            class="tab-panel"
            role="tabpanel"
            aria-labelledby="tab-comparacao"
          >
            <ComparisonPanel
              :kruskal="runResponse?.kruskal ?? null"
              :prim="runResponse?.prim ?? null"
              :comparison="runResponse?.comparison ?? null"
              :names="names"
            />
          </section>

          <section
            v-show="activeTab === 'passo'"
            id="panel-passo"
            class="tab-panel"
            role="tabpanel"
            aria-labelledby="tab-passo"
          >
            <div v-if="traceEvents.length === 0" class="empty-state">
              <h3>Passo a passo indisponível</h3>
              <p v-if="!runResponse">
                Execute os algoritmos com a opção <strong>Gerar passo a passo</strong>
                marcada para acompanhar cada decisão.
              </p>
              <p v-else-if="!traceEnabled">A última execução foi feita sem o rastro de eventos.</p>
              <p v-else>O resultado atual não contém eventos de passo a passo.</p>
              <button type="button" class="primary-button" @click="runWithTrace">
                Executar com passo a passo
              </button>
            </div>

            <template v-else>
              <div v-if="hasBoth" class="result-toolbar">
                <span class="muted small">Passo a passo de</span>
                <div class="segmented compact" role="group" aria-label="Rastro exibido">
                  <button
                    type="button"
                    :class="{ active: traceAlgorithm === 'kruskal' }"
                    :aria-pressed="traceAlgorithm === 'kruskal'"
                    :disabled="!runResponse?.kruskal?.trace"
                    @click="selectTraceAlgorithm('kruskal')"
                  >
                    Kruskal
                  </button>
                  <button
                    type="button"
                    :class="{ active: traceAlgorithm === 'prim' }"
                    :aria-pressed="traceAlgorithm === 'prim'"
                    :disabled="!runResponse?.prim?.trace"
                    @click="selectTraceAlgorithm('prim')"
                  >
                    Prim
                  </button>
                </div>
              </div>

              <StepPlayer
                v-model:index="traceIndex"
                :algorithm="traceAlgorithm"
                :events="traceEvents"
                :snapshot="traceSnapshot"
              />
            </template>
          </section>

          <section
            v-show="activeTab === 'benchmark'"
            id="panel-benchmark"
            class="tab-panel"
            role="tabpanel"
            aria-labelledby="tab-benchmark"
          >
            <BenchmarkPanel :graph="graph" :graph-label="graphLabel" />
          </section>

          <section
            v-show="activeTab === 'teoria'"
            id="panel-teoria"
            class="tab-panel prose-panel"
            role="tabpanel"
            aria-labelledby="tab-teoria"
          >
            <TheoryPanel />
          </section>

          <section
            v-show="activeTab === 'modelagem'"
            id="panel-modelagem"
            class="tab-panel prose-panel"
            role="tabpanel"
            aria-labelledby="tab-modelagem"
          >
            <ModelingPanel />
          </section>
        </section>
      </main>
    </div>

    <footer class="app-footer">
      <p>
        Dados: malha municipal 2024 do IBGE (<em>Municípios Limítrofes</em>) e coordenadas de sedes
        do repositório <code>kelvins/municipios-brasileiros</code>, baixados em 08/11/2026. Consulte
        <code>data/FONTES.md</code>.
      </p>
      <p>
        Implementação didática de Prim e Kruskal sem bibliotecas de grafos no código de execução. O
        projeto é local e não envia dados a serviços externos.
      </p>
    </footer>
  </div>
</template>
