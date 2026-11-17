# Arquitetura — Árvore Geradora Mínima

Documento de arquitetura da aplicação "Árvore Geradora Mínima — Municípios de São Paulo". Descreve o contrato da API, as camadas do backend, o frontend, as fronteiras entre camadas e as principais decisões arquiteturais.

O schema OpenAPI da API está publicado em [`docs/openapi.json`](./openapi.json) e pode ser visualizado interativamente em `/docs` (Swagger UI) enquanto o servidor estiver rodando.

## 1. Visão geral

A aplicação é uma API web local construída com **FastAPI** (Python 3) que modela a malha de municípios de São Paulo como um grafo ponderado e calcula a árvore geradora mínima (MST) com os algoritmos de **Prim** e **Kruskal**, implementados do zero. O frontend é uma aplicação separada (**Vue 3 + TypeScript + Vite**) compilada em `frontend/dist` e servida como arquivos estáticos pelo próprio backend em produção.

## 2. Contrato da API

O endpoint de saúde `/health` não tem prefixo. Todos os demais endpoints estão sob o prefixo `/api/v1`. A API troca JSON e segue os modelos Pydantic definidos em `backend/app/api/schemas.py`.

| Endpoint | Método | Descrição | Resposta principal |
|----------|--------|-----------|--------------------|
| `/health` | GET | Verificação de que o servidor está no ar | `HealthResponse` (`{status: "ok"}`) |
| `/api/v1/cities` | GET | Lista pesquisável de municípios, com vizinhos para o atalho do frontend | `CitiesResponse` |
| `/api/v1/presets` | GET | Resumo das instâncias prontas de grafo | `PresetsResponse` |
| `/api/v1/presets/{id}` | GET | Grafo completo de uma instância pronta | `PresetDetailDTO` |
| `/api/v1/graph/build` | POST | Monta o subgrafo induzido por uma seleção de municípios, opcionalmente expandindo a seleção por vizinhos até ficar conexo | `GraphDTO` |
| `/api/v1/graph/upload` | POST | Recebe CSV ou JSON, valida e devolve o grafo (ou erro legível) | `UploadResponseDTO` |
| `/api/v1/run` | POST | Executa Kruskal, Prim ou ambos, com trace e verificação opcionais | `RunResponse` |
| `/api/v1/benchmark` | POST | Executa análise de tempo por tamanho de instância | `BenchmarkResponse` |

### Modelos principais

- **`GraphDTO`** — grafo de entrada/saída: `nodes` (`NodeDTO[]`), `edges` (`EdgeDTO[]`), `warnings`, `discarded` (`DiscardedDTO[]`) e `stats` (`GraphStatsDTO`).
- **`EdgeDTO`** — aresta com `u`, `v`, `weight` e `attrs` (metadados opcionais).
- **`RunRequest`** — exige exatamente um entre `graph` ou `preset_id`; `algorithm` ∈ `{kruskal, prim, both}`; `trace` e `verify` são opcionais.
- **`RunResponse`** — resultados de `kruskal` e/ou `prim` (`MSTResultDTO`), `comparison` (`ComparisonDTO`), `verification` e `graph_stats`.
- **`ErrorResponse`** — envelope de erro padronizado: `{ error: { code, message, details } }`.

Os erros são mapeados para códigos de status HTTP: `422` (validação), `500` (erro de carregamento de dados ou interno inesperado). Todas as respostas de erro seguem o formato `ErrorResponse`.

## 3. Frontend

A aplicação frontend fica em `frontend/` e é construída com **Vue 3 + TypeScript + Vite**, servida na máquina do desenvolvedor pelo Vite (porta `5173`, com proxy `/api` para o backend) e em produção compilada em `frontend/dist`, servida pelo próprio backend como arquivos estáticos.

### 3.1. Stack

- Node 22 (`.nvmrc`)
- Vue 3.5.45
- Vite 8.3.6
- TypeScript 5.9.3

### 3.2. Componentes

Todos os componentes de interface ficam em `frontend/src/components/`:

- `App.vue` — raiz da aplicação; concentra o estado centralizado (cidades, presets, grafo carregado, resultados, abas ativas, erros).
- `GraphCanvas` — renderização do grafo, vértices e arestas (incluindo destaque do passo atual e arestas da MST).
- `CitySelector` — seleção de municípios para montar o subgrafo.
- `UploadPanel` — envio de arquivo CSV/JSON com o grafo.
- `ResultPanel` — exibição do resultado de um algoritmo (Kruskal ou Prim).
- `MetricsTable` — tabela de métricas do grafo/resultado.
- `MstEdgeTable` — tabela das arestas escolhidas na MST.
- `ComparisonPanel` — comparação lado a lado entre Kruskal e Prim.
- `StepPlayer` — reprodução do rastro passo a passo (`trace`) de um algoritmo.
- `BenchmarkPanel` — execução e exibição do benchmark de desempenho.
- `BenchmarkChart` — gráfico de tempo por tamanho de instância.
- `TheoryPanel` — conteúdo teórico sobre árvores geradoras mínimas.
- `ModelingPanel` — conteúdo sobre modelagem do problema como grafo.
- `WarningsPanel` — avisos sobre o grafo carregado (arestas descartadas, etc.).
- `VerificationBadges` — selos de verificação da validade da MST.

O estado da aplicação é centralizado em `App.vue`; os componentes recebem dados via props e emitem eventos. A camada de acesso à API fica em `frontend/src/api/client.ts` e chama os endpoints sob `/api/v1/*`.

### 3.3. Testes do frontend

- Testes unitários (Vitest): `frontend/src/**/*.test.ts` (um arquivo de teste por componente e pela camada de API).
- Testes E2E (Playwright): `frontend/e2e/fluxos.spec.ts`.

## 4. Camadas do backend

O código-fonte fica em `backend/app/` e está organizado em camadas, de fora para dentro:

### 4.1. Camada de transporte / API (`api/`)

Responsabilidade: expor endpoints HTTP, serializar requisições/respostas e traduzir HTTP para os serviços de domínio.

- `main.py` — instância FastAPI, middlewares (CORS e cabeçalhos de segurança), montagem de arquivos estáticos do frontend (`frontend/dist`), handlers globais de exceção e endpoint `/health`.
- `api/routes.py` — roteador com prefixo `/api/v1`; cada endpoint apenas recebe o payload, chama o serviço correspondente e retorna o DTO.
- `api/schemas.py` — modelos Pydantic que definem o contrato da API (DTOs, requests e `ErrorResponse`).

### 4.2. Camada de serviços (`services/`)

Responsabilidade: orquestrar casos de uso e conter a regra de negócio da aplicação.

- `presets.py` — instâncias prontas de grafo (presets).
- `graph_selection.py` — constrói subgrafos induzidos por seleção de municípios e catálogo de cidades.
- `uploads.py` — parsing e validação de arquivos CSV/JSON enviados.
- `run_service.py` — executa os algoritmos de MST sobre um grafo.
- `serialization.py` — conversão de grafo interno para dicionário/DTO.
- `benchmark.py` — análise de desempenho por tamanho de instância.

### 4.3. Camada de algoritmos / domínio (`algorithms/`)

Responsabilidade: implementação dos algoritmos de grafos e estruturas de dados, sem dependência do FastAPI.

- `graph.py` — modelo `Graph`, validação e construção a partir de registros.
- `union_find.py` — estrutura conjunto-disjunto (usada por Kruskal).
- `kruskal.py` — algoritmo de Kruskal (com rastreamento passo a passo).
- `prim.py` — algoritmo de Prim.
- `result.py` — montagem de resultados de MST.
- `verify.py` — verificação de validade da MST (floresta, propriedade do ciclo, custo consistente).

### 4.4. Camada de dados e infraestrutura

- `data_loader.py` — carregamento dos dados dos municípios a partir de `data/processed/`.
- `errors.py` — erros de domínio (`DomainError`, `ValidationError`, `PayloadTooLargeError`, `DataLoadError`, etc.).

## 5. Fronteiras entre camadas

A dependência flui em uma única direção: **transporte → serviços → algoritmos/dados**. Nenhuma camada interna conhece a camada externa.

| Fronteira | Direção | O que atravessa | Mecanismo |
|-----------|---------|-----------------|-----------|
| Cliente ↔ API | bidirecional | JSON | HTTP + Pydantic (validação automática de request/response) |
| API → Serviços | saída | DTOs Pydantic / dicts | Chamada direta de função nos endpoints de `routes.py` |
| Serviços → Algoritmos | saída | Objetos `Graph` (domínio) | Chamada direta a `algorithms.*` |
| Algoritmos → Dados | leitura | Registros de cidade/aresta | `data_loader.py` |

Regras de fronteira:

1. **As rotas não contêm regra de negócio.** Elas apenas traduzem HTTP para serviços e tratam exceções convertendo-as em respostas `ErrorResponse`.
2. **Os serviços não conhecem FastAPI.** Não importam `Request`, `UploadFile` do framework diretamente (exceto o parâmetro de arquivo no endpoint, tratado na rota); trabalham com dados puros.
3. **Os algoritmos são puros e independentes.** `algorithms/` não importa nada do `fastapi`, `pydantic` ou dos serviços; recebe e retorna estruturas de dados simples.
4. **Erros de domínio são traduzidos na camada de transporte.** `main.py` registra handlers globais que convertem `DomainError`, `GraphValidationError`, `RequestValidationError`, `DataLoadError` e exceções inesperadas em `ErrorResponse` com o status HTTP adequado.

## 6. Stack e versões

### Backend (Python)

| Pacote | Versão |
|--------|--------|
| FastAPI | 0.162.2 |
| Uvicorn | 0.54.0 |
| Pydantic | 2.14.3 |
| python-multipart | 0.0.33 |

Dependências de desenvolvimento (pytest): pytest 9.2.0 (entre outras listadas em `pyproject.toml`).

### Frontend (Node/Vue)

| Pacote | Versão |
|--------|--------|
| Node | 22 |
| Vue | 3.5.45 |
| Vite | 8.3.6 |
| TypeScript | 5.9.3 |

### Testes

| Ferramenta | Versão |
|----------|--------|
| pytest | 9.2.0 |
| Vitest | 5.1.0 |
| Playwright | 1.65.1 |

## 7. Como executar

O ponto de entrada é `run.py`:

```bash
python run.py
python run.py --port 8080 --no-browser --reload
```

Argumentos aceitos:

- `--host` — endereço de escuta (padrão: `127.0.0.1`).
- `--port` — porta HTTP (padrão: `8000`).
- `--no-browser` — não abrir o navegador automaticamente.
- `--reload` — recarregar o servidor ao alterar arquivos (desenvolvimento).

Por padrão o navegador é aberto automaticamente após **1,2 segundos**. O backend serve o frontend compilado em `frontend/dist` na raiz (`/`). Não há banco de dados nem serviço externo em tempo de execução; todos os dados são lidos de arquivos locais em `data/processed/`.

Quando `frontend/dist` não existe, a raiz retorna uma página informativa orientando a compilação (`cd frontend && npm install && npm run build`) ou o uso do modo de desenvolvimento do Vite.

## 8. Dados

- `data/processed/` — usado em execução (`cities.csv`, `edges.csv`).
- `data/raw/` — **não** é usado em execução; serve apenas como entrada do script de preparação.
- `data/manual/extras.csv` — contém a ligação por balsa (Ilhabela–São Sebastião), incluída como aresta manual.
- `scripts/build_dataset.py` — preparação offline dos dados a partir dos arquivos brutos do IBGE (ODS/CSV) usando `odfpy`; grava os resultados em `data/processed/`. Não faz parte da aplicação em execução.

## 9. Testes

- Backend: testes em `tests/` (executados com pytest).
- Frontend unitário: `frontend/src/**/*.test.ts` (executados com Vitest).
- Frontend E2E: `frontend/e2e/fluxos.spec.ts` (executados com Playwright).

## 10. Como gerar o OpenAPI

O schema é gerado a partir da instância FastAPI em `backend/app/main.py`:

```bash
python -c "import json; from backend.app.main import app; print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))" > docs/openapi.json
```

O arquivo `docs/openapi.json` deve ser regenerado sempre que houver mudança nos endpoints ou nos esquemas Pydantic.

## 11. Estrutura de diretórios relevante

```
backend/app/
├── main.py            # App FastAPI, middlewares, handlers de erro, /health, estáticos
├── api/
│   ├── routes.py      # Endpoints HTTP com prefixo /api/v1 (transporte)
│   └── schemas.py     # Modelos Pydantic (contrato da API)
├── services/          # Casos de uso / regra de negócio
│   ├── presets.py
│   ├── graph_selection.py
│   ├── uploads.py
│   ├── run_service.py
│   ├── serialization.py
│   └── benchmark.py
├── algorithms/        # Domínio: grafos e MST (sem FastAPI)
│   ├── graph.py
│   ├── union_find.py
│   ├── kruskal.py
│   ├── prim.py
│   ├── result.py
│   └── verify.py
├── data_loader.py     # Carregamento de dados dos municípios (data/processed/)
└── errors.py          # Erros de domínio

frontend/
├── src/
│   ├── App.vue        # Estado centralizado e raiz da aplicação
│   ├── main.ts
│   ├── types.ts
│   ├── api/
│   │   └── client.ts  # Chamadas aos endpoints /api/v1/*
│   ├── components/    # GraphCanvas, CitySelector, UploadPanel, ResultPanel,
│   │   │              # MetricsTable, MstEdgeTable, ComparisonPanel, StepPlayer,
│   │   │              # BenchmarkPanel, BenchmarkChart, TheoryPanel, ModelingPanel,
│   │   │              # WarningsPanel, VerificationBadges
│   └── **/*.test.ts   # Testes unitários (Vitest)
├── e2e/
│   └── fluxos.spec.ts # Testes E2E (Playwright)
├── dist/              # Build compilado, servido pelo backend
├── package.json
├── vite.config.ts
├── vitest.config.ts
└── playwright.config.ts

data/
├── processed/         # Usado em execução (cities.csv, edges.csv)
├── raw/               # Entrada do build_dataset.py (não usado em execução)
├── manual/
│   └── extras.csv     # Ligação manual por balsa
└── FONTES.md

scripts/
└── build_dataset.py   # Preparação offline com odfpy

tests/                 # Testes do backend (pytest)
docs/
├── openapi.json       # Schema OpenAPI exportado
└── ARCHITECTURE.md    # Este documento
```
