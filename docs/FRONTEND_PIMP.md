# Frontend: o que foi feito, como e por quê

Este documento registra a decisão de usar um framework JavaScript no frontend,
o que foi construído, como funciona e quais são as consequências para a
apresentação. O usuário autorizou explicitamente o uso de Node/build e pediu
que a decisão fosse documentada.

## Decisão: Vue 3 + Vite + TypeScript

O `PLAN.md` sugeria HTML, CSS e JavaScript puro com Canvas 2D. Em vez disso, o
frontend foi construído com:

- **Vue 3** (`<script setup>` + Composition API);
- **Vite** para desenvolvimento e build;
- **TypeScript** para tipar o contrato da API;
- **Canvas 2D** para o grafo e para o gráfico do benchmark;
- **CSS próprio**, sem biblioteca de componentes e sem CDN.

### Por que Vue

1. **Estado compartilhado**: a tela tem uma execução, dois algoritmos, trace,
   abas, seleção de cidades, upload e benchmark. Vue reatividade evita
   sincronização manual de DOM.
2. **Componentização**: canvas, tabelas, painéis de teoria/modelagem, passo a
   passo e benchmark ficam isolados e testáveis.
3. **Legibilidade para a apresentação**: o fluxo `estado → template` é mais
   fácil de explicar do que dezenas de manipuladores de DOM espalhados.
4. **TypeScript**: o contrato Pydantic da API foi espelhado em
   `frontend/src/types.ts`; erros de campo aparecem no `vue-tsc` antes de
   chegar ao navegador.

O custo aceito é que **Node é necessário para desenvolver ou recompilar** o
frontend. Isso não afeta a apresentação: o resultado compilado é versionado em
`frontend/dist` e servido pelo próprio FastAPI.

## Como o frontend é servido

- Em produção/apresentação: `python run.py` sobe o FastAPI, que monta
  `frontend/dist` na raiz `/`. As rotas `/api`, `/docs` e `/health` continuam
  tendo prioridade. Não é necessário Node, npm ou internet.
- Em desenvolvimento: `npm run dev` sobe o Vite na porta 5173 e faz proxy de
  `/api` e `/health` para `http://127.0.0.1:8000`.
- O build verifica tipos e gera os arquivos com `vue-tsc --noEmit && vite build`.

Para recompilar depois de alterar o frontend:

```bash
cd frontend
npm install
npm run build
```

O conteúdo de `frontend/dist` deve ser commitado junto com a alteração para que
a apresentação funcione em uma máquina sem Node.

## Estrutura

```
frontend/
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
├── dist/                     # build versionado, servido pelo FastAPI
└── src/
    ├── App.vue               # estado global, layout, abas e ações
    ├── main.ts
    ├── style.css             # tokens, componentes, responsividade
    ├── types.ts              # contrato da API em TypeScript
    ├── api/client.ts         # fetch tipado + ApiError
    ├── components/
    │   ├── GraphCanvas.vue
    │   ├── CitySelector.vue
    │   ├── UploadPanel.vue
    │   ├── ResultPanel.vue
    │   ├── ComparisonPanel.vue
    │   ├── MetricsTable.vue
    │   ├── MstEdgeTable.vue
    │   ├── VerificationBadges.vue
    │   ├── WarningsPanel.vue
    │   ├── StepPlayer.vue
    │   ├── BenchmarkChart.vue
    │   ├── BenchmarkPanel.vue
    │   ├── TheoryPanel.vue
    │   └── ModelingPanel.vue
    └── lib/
        ├── format.ts         # números e tempos em pt-BR
        ├── graph.ts          # componentes, nomes, paleta
        ├── layout.ts         # projeção geográfica e layout circular
        ├── pseudocode.ts     # pseudocódigo de Kruskal e Prim
        ├── text.ts           # normalização de busca e chave de aresta
        └── trace.ts          # snapshots e explicações do passo a passo
```

## O que cada parte faz

### Fonte do grafo

- **Instâncias prontas**: carrega `GET /api/presets/{id}` e executa os
  algoritmos automaticamente com os parâmetros atuais.
- **Selecionar municípios**: usa o catálogo de `GET /api/cities`, permite busca
  por nome/código, adicionar vizinhos, limpar e incluir/excluir a ligação
  manual. Inclui um toggle de **conexão automática** (apenas neste modo) que,
  ao montar, expande a seleção por vizinhos até o grafo ficar conexo.
  Envia `POST /api/graph/build` com o campo `connect_components`.
- **Arquivo**: envia CSV ou JSON para `POST /api/graph/upload`, com exemplos em
  `examples/`.

### Visualização

`GraphCanvas.vue` desenha em Canvas 2D:

- posições por longitude/latitude com correção `cos(latitude média)`; layout
  circular quando o grafo não tem coordenadas;
- zoom pela roda do mouse, pan por arraste e restauração do enquadramento;
- arestas comuns, arestas da MST, aresta atual do trace, ligações manuais
  tracejadas e divisas curtas opcionais;
- cores por componente quando o resultado é uma floresta;
- dica com nome, código IBGE e grau ao passar o mouse;
- clique em um vértice define o início do Prim (e muda para “Ambos” se o
  usuário estava em Kruskal).

O canvas foi escolhido em vez de SVG porque a instância `p3` tem 644 vértices e
1.832 arestas. Desenhar milhares de elementos SVG a cada passo seria lento.

### Resultado, comparação e verificação

- `ResultPanel` mostra custo, arestas aceitas, componentes, tempo, métricas,
  verificação e a tabela de arestas escolhidas.
- `ComparisonPanel` mostra os dois algoritmos lado a lado, o veredito de
  consistência, empates, diferenças de arestas e complexidades.
- `VerificationBadges` exibe a verificação independente (estrutura, propriedade
  do ciclo e consistência de custo).

### Passo a passo

O backend devolve o trace quando `trace=true`. O frontend não reimplementa os
algoritmos: ele percorre os eventos e reconstrói o estado até o índice atual em
`lib/trace.ts`:

- arestas aceitas até o momento;
- aresta atual;
- contadores (examinadas, aceitas, rejeitadas/descartadas, inserções e
  extrações);
- explicação teórica em pt-BR;
- linha do pseudocódigo destacada.

`StepPlayer` oferece reproduzir/pausar, passo a passo, velocidade e barra de
progresso. O canvas usa o prefixo da árvore e a aresta atual, então a animação
e o desenho ficam sincronizados.

### Benchmark

`BenchmarkPanel` chama `POST /api/benchmark` com o grafo carregado e exibe
mediana e faixa p25–p75 em subgrafos induzidos crescentes até o grafo completo.
`BenchmarkChart` é um gráfico de linhas em Canvas 2D, com escala logarítmica no
eixo de vértices, faixas de dispersão e dica interativa. A tabela ao lado traz
os valores exatos.

### Teoria e modelagem

`TheoryPanel` e `ModelingPanel` são conteúdo estático em pt-BR, alinhado ao
`PLAN.md`: definição de árvore geradora, propriedades do corte e do ciclo,
Kruskal, Prim, esparso × denso, modelagem do grafo e limitações.

## Contrato e tratamento de erros

- `types.ts` espelha os DTOs Pydantic de `backend/app/api/schemas.py`.
- `api/client.ts` centraliza `fetch`, converte erros HTTP no tipo `ApiError` e
  preserva `code`, `message` e `details` para a interface.
- Erros aparecem em um painel global com a mensagem em pt-BR e a lista de
  detalhes; a interface não quebra nem perde o grafo atual.
- Toda execução envia o grafo completo em `POST /api/run`, com `algorithm`,
  `start_vertex`, `trace` e `verify`.

## Acessibilidade e responsividade

- Rótulos associados a inputs, `aria-live` nos avisos e explicações, papéis
  `tablist`/`tab`/`tabpanel`, foco visível e textos alternativos nos canvas.
- Layout em duas colunas no desktop, uma coluna no tablet e ajustes para telas
  pequenas; tabelas têm rolagem horizontal.
- `prefers-reduced-motion` desliga animações e transições.
- Cores com contraste suficiente; a legenda não depende apenas de cor (usa
  também tracejado para ligações manuais).

## Limitações e decisões conscientes

- **Sem biblioteca de grafos no frontend**: layout, componentes e trace são
  implementados localmente. Não há D3, Cytoscape, vis-network ou similar.
- **Sem CDN e sem serviço externo**: fontes do sistema, CSS e JS locais.
- **O grafo é redesenhado no cliente** a partir do DTO; não há imagem de mapa.
  Isso mantém o sistema offline e permite zoom/pan sem tiles.
- **O build versionado aumenta o repositório** em poucos arquivos (~160 KB de
  JS + CSS antes de gzip). O benefício é rodar na apresentação sem Node.
- **O frontend não é um pacote publicado**: `package-lock.json` fixa as versões
  usadas no build.
- **Testes de UI** foram feitos com Playwright em navegador headless durante o
  desenvolvimento (carregamento, abas, passo a passo, comparação, benchmark,
  layout móvel). O projeto não inclui uma suíte E2E versionada porque o escopo
  obrigatório de testes é o backend/algoritmos; a verificação manual está
  registrada em `docs/AI_USAGE_LOG.md`.
