# Árvore Geradora Mínima — Municípios de São Paulo

Sistema web local que modela a malha municipal de São Paulo como um grafo
ponderado e calcula a **árvore geradora mínima (AGM)** com **Prim** e
**Kruskal**, ambos implementados do zero. A interface permite visualizar o
grafo, escolher instâncias, montar o próprio grafo, enviar arquivos, comparar os
dois algoritmos, acompanhar o passo a passo e medir tempos de execução.

**Integrantes:** Leonardo Enzo Lanzoni Inacio, Davi Medrano Guido, José Paulo Dassie Felippi, Guilherme Ribeiro Zagrande, Eduardo Ticianelli Chacon Botare

> Este repositório é a documentação e o código do projeto. O **relatório
> técnico** é um documento à parte, fora do escopo deste repositório.

## O problema

O problema modelado é o de projetar uma rede de interligação de menor custo
total entre municípios: cada município é um vértice e cada divisa entre dois
municípios é uma aresta, com peso igual à distância aproximada entre as sedes.
A AGM indica quais ligações escolher para conectar todos os municípios com o
menor custo total.

## Modelagem do grafo

- **Vértices:** os **645 municípios de São Paulo**, identificados pelo **código
  IBGE de 7 dígitos**. Cada vértice tem nome, latitude e longitude da sede.
- **Arestas:** par de municípios **vizinhos**, isto é, que fazem divisa (é
  possível sair de um e chegar ao outro sem passar por município
  intermediário).
  - Origem principal: planilha *Municípios Limítrofes* do IBGE
    (`source = divisa`).
  - Exceção documentada: ligações que não são divisa terrestre, mantidas em
    `data/manual/extras.csv` (`source = manual`). Hoje há uma: **Ilhabela ↔
    São Sebastião**, por balsa.
- **Tipo:** **não direcionado**, **ponderado** e **simples** (sem laços e sem
  arestas paralelas).
- **Peso:** distância em km entre as sedes, pela **fórmula de Haversine**
  (raio da Terra = 6.371,0088 km). Interpretação: aproximação do custo de
  lançar uma ligação.
- **Atributos extras da aresta (não são o peso):**
  - `border_km`: extensão da divisa no IBGE;
  - `source`: `divisa` ou `manual`;
  - `short_border`: verdadeiro quando a divisa tem menos de 0,5 km.

### Hipóteses e limitações

1. A distância em linha reta entre sedes **não** é a distância por rodovia. O
   custo real dependeria de relevo, faixa de domínio, desapropriações etc.
2. A vizinhança vem da malha municipal de 2024 do IBGE. Os dados do IBGE são
   referenciais e têm finalidade estatística.
3. Divisas muito curtas (`short_border`) são mantidas: o município toca o
   outro sem intermediário. É uma decisão do projeto, não um fato absoluto.
4. Municípios fora da seleção do usuário são ignorados: o grafo é o
   **subgrafo induzido** pela seleção.
5. Se o grafo for **desconexo**, não existe árvore geradora. O sistema calcula
   a **floresta geradora mínima** (uma AGM por componente) e avisa.
6. Três nomes divergem entre as fontes (Biritiba Mirim, Florínea e Itaoca). A
   junção é sempre pelo **código IBGE**, nunca pelo nome; a grafia exibida é a
   da planilha do IBGE.
7. A **conexão automática** expande a seleção adicionando todos os vizinhos dos
   municípios selecionados, em rodadas, até o grafo ficar conexo. Dependendo da
   distância entre as cidades, isso pode adicionar muitos municípios (em casos
   extremos, quase todo o componente principal do estado) e é avisado na
   interface.

## Funcionalidades

- **Instâncias prontas:**
  - `p1-bauru-vizinhos` — Bauru e vizinhos diretos (8 vértices, 15 arestas);
  - `p2-regiao-bauru` — região de Bauru (109 vértices, 295 arestas);
  - `p3-estado-sp` — maior componente conexo do estado (644 vértices, 1.832
    arestas), com Ilhabela descartada por ficar isolada sem a balsa;
  - `p4-regioes-separadas` — duas regiões desconexas (20 vértices, 37 arestas,
    floresta com 2 componentes);
  - `p5-litoral-norte` — Ilhabela, São Sebastião, Bertioga e Caraguatatuba,
    incluindo a ligação manual por balsa.
- **Seleção de municípios:** busca por nome ou código IBGE, seleção múltipla,
  atalho para adicionar vizinhos, opção de incluir a ligação manual, montagem
  do subgrafo induzido e **conexão automática** (adiciona vizinhos em rodadas
  até que os municípios escolhidos formem um único grafo, com aviso das cidades
  adicionadas e inclusão automática da balsa quando necessária).
- **Upload CSV/JSON:** formatos de lista de arestas, com validação, avisos e
  erros com número de linha. Exemplos em `examples/`.
- **Execução de Kruskal, Prim ou ambos**, com escolha do vértice inicial do
  Prim e destaque das arestas escolhidas sobre o grafo.
- **Resultado:** custo total, número de arestas, componentes, tempo, métricas,
  verificação independente e tabela de arestas com nomes, códigos IBGE,
  distância e origem.
- **Comparação Prim × Kruskal:** custo, conjunto de arestas, empates, diferenças
  e complexidades teóricas.
- **Passo a passo:** reproduzir/pausar, avançar/voltar, velocidade, barra de
  progresso, aresta atual, contadores, explicação teórica e pseudocódigo com a
  linha atual destacada.
- **Verificação de otimalidade:** estrutura de floresta, propriedade do ciclo e
  consistência de custo, sem chamar os algoritmos.
- **Benchmark:** mediana e faixa p25–p75 de Kruskal e Prim em subgrafos
  crescentes do grafo carregado (até o grafo completo), com tabela e gráfico em
  canvas.
- **Conteúdo teórico:** painéis “Teoria” e “Modelagem” com definições,
  propriedades do corte e do ciclo, complexidades e limitações.
- **Avisos visíveis:** grafo desconexo, cidades descartadas, seleção
  insuficiente, arquivo inválido, laços, arestas duplicadas e pesos negativos.
- **Visualização:** canvas com zoom, pan, dica com nome/código/grau, cores por
  componente, ligações manuais tracejadas e alternância de divisas curtas.

## Tecnologias e dependências

### Execução

- **Python 3.12 ou superior** — maior exigência entre as dependências do
  projeto (NetworkX 3.7, usado apenas nos testes, requer 3.12+). Versão usada
  no desenvolvimento e na apresentação: **Python 3.14.10**.
- `fastapi==0.162.2`
- `uvicorn[standard]==0.54.0`
- `pydantic==2.14.3`
- `python-multipart==0.0.33`
- O frontend compilado (`frontend/dist`) é servido pelo FastAPI. **Node não é
  necessário para executar o sistema** na apresentação.

### Desenvolvimento e testes

- `pytest==9.2.0`
- `pytest-cov==7.1.0`
- `httpx==0.28.1`
- `networkx==3.7` (**somente nos testes**)
- `odfpy==1.4.1` (somente para regenerar os dados a partir do arquivo ODS)
- **Node.js 22.13 ou superior + npm** apenas para desenvolver ou recompilar o
  frontend: Vue 3, Vite e TypeScript (versões fixadas em
  `frontend/package-lock.json`).

### Declaração de bibliotecas de grafos

**Nenhuma biblioteca de grafos é usada no código de execução.** Grafo,
Union-Find, Kruskal, Prim, verificação, layout e desenho são implementados no
projeto. **NetworkX é usado exclusivamente em `tests/`**, para conferir o custo
das soluções em grafos aleatórios.

## Instalação e execução

### Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

### Windows (PowerShell ou Prompt de Comando)

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

O comando abre o navegador em `http://127.0.0.1:8000`. Para não abrir
automaticamente:

```bash
python run.py --no-browser
```

Para usar outra porta:

```bash
python run.py --port 8080 --no-browser
```

A especificação OpenAPI fica em `http://127.0.0.1:8000/openapi.json` (cópia
versionada em `docs/openapi.json`) e a documentação interativa (Swagger UI) em
`http://127.0.0.1:8000/docs`. O sistema é **local e offline**: não há banco de
dados nem serviço externo em tempo de execução; apenas a página do Swagger UI
carrega assets via CDN.

### Recompilar o frontend (opcional)

Só é necessário ao alterar arquivos de `frontend/src/`:

```bash
cd frontend
npm install
npm run build
```

O build roda `vue-tsc --noEmit` (verificação de tipos) e `vite build`, gerando
`frontend/dist`. Esse diretório é versionado para que a apresentação rode sem
Node. A decisão e a arquitetura do frontend estão em
[`docs/FRONTEND_PIMP.md`](docs/FRONTEND_PIMP.md).

## Como usar

1. Abra o sistema; a instância `p1` é carregada e executada automaticamente.
2. No painel esquerdo, escolha uma instância pronta, selecione municípios ou
   envie um arquivo.
3. Defina o algoritmo (Kruskal, Prim ou ambos), o vértice inicial do Prim, e se
   deseja gerar o passo a passo e a verificação.
4. Clique em **Executar algoritmos**.
5. Veja o resultado, a comparação, o passo a passo, o benchmark, a teoria e a
   modelagem nas abas.
6. No canvas, arraste para mover, use a roda do mouse para ampliar e clique em
   um vértice para defini-lo como início do Prim.

### Formato dos arquivos de upload

**CSV** — lista de arestas, com cabeçalho `origem,destino,peso` (ou
`source,target,weight`), separador `,` ou `;`, ponto ou vírgula decimal:

```csv
origem,destino,peso
A,B,12.5
B,C,7
```

**JSON** — objeto com `nodes` (opcional) e `edges`:

```json
{
  "nodes": [
    { "id": "A", "name": "Opcional", "lat": -22.3, "lon": -49.0 }
  ],
  "edges": [
    { "source": "A", "target": "B", "weight": 12.5 }
  ]
}
```

Exemplos válidos e inválidos estão em [`examples/`](examples/README.md).

## Dados

- **Malha municipal 2024 do IBGE** — *Municípios Limítrofes*:
  <https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/42224-municipios-limitrofes.html>
- **Coordenadas das sedes** — repositório `kelvins/municipios-brasileiros`
  (licença MIT): <https://github.com/kelvins/municipios-brasileiros>
- **Data do download:** 08/11/2026.

Os arquivos brutos ficam em `data/raw/`. O sistema em execução lê **apenas**
`data/processed/`, que é versionado:

- `data/processed/cities.csv`: 645 municípios;
- `data/processed/edges.csv`: 1.832 divisas + 1 ligação manual = 1.833 arestas;
- `data/manual/extras.csv`: ligações manuais documentadas.

Para regenerar os dados processados (requer `odfpy` e os arquivos brutos):

```bash
pip install -r requirements-dev.txt
python scripts/build_dataset.py
```

O script valida os fatos conhecidos (645 municípios, 1.832 divisas, Ilhabela
isolada, simetria, grafias divergentes, contagens de divisas curtas) e falha
com mensagem clara se algo divergir. Detalhes de origem, licença e limitações
em [`data/FONTES.md`](data/FONTES.md).

### Valor de referência

A AGM do maior componente do grafo de divisas de São Paulo tem **643 arestas** e
custo aproximado de **9.034,325 km** (Haversine, R = 6.371,0088 km). Esse valor
é usado como teste de regressão.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

Com relatório de cobertura:

```bash
pytest --cov=backend --cov-report=term-missing
```

A suíte cobre:

- algoritmos em grafos pequenos calculados à mão, com empates e pesos
  negativos;
- casos sem solução/desconexos, fronteira e validação de entrada;
- comparação com NetworkX em grafos aleatórios;
- dados reais e valor de referência da AGM;
- presets, incluindo o caso grande `p3` e a floresta `p4`;
- API com `TestClient`, erros legíveis e limite de upload;
- uploads CSV/JSON válidos e inválidos, incluindo os exemplos;
- benchmark e metadados.

Resultado atual: **426 testes passando** (o número pode crescer com novas
verificações).

## Estrutura do repositório

```
.
├── README.md
├── requirements.txt / requirements-dev.txt
├── run.py                     # sobe o FastAPI e abre o navegador
├── data/
│   ├── raw/                   # arquivos brutos (não usados em execução)
│   ├── manual/extras.csv      # ligações manuais documentadas
│   ├── processed/             # cities.csv e edges.csv (versionados)
│   └── FONTES.md
├── scripts/
│   └── build_dataset.py       # prepara data/processed a partir de data/raw
├── backend/app/
│   ├── main.py                # app FastAPI, erros e estáticos
│   ├── data_loader.py         # leitura de data/processed
│   ├── errors.py              # erros de domínio
│   ├── api/                   # rotas e esquemas Pydantic
│   ├── algorithms/            # graph, union_find, kruskal, prim, verify, result
│   └── services/              # presets, seleção, uploads, execução, benchmark
├── frontend/
│   ├── src/                   # Vue 3 + TypeScript
│   ├── dist/                  # build servido pelo FastAPI (versionado)
│   └── package.json
├── examples/                  # arquivos CSV/JSON de exemplo
├── tests/                     # pytest; NetworkX somente aqui
└── docs/
    ├── AI_USAGE_LOG.md        # transparência no uso de IA
    ├── ARCHITECTURE.md        # contrato da API e decisões de arquitetura
    ├── FRONTEND_PIMP.md       # decisão e arquitetura do frontend
    └── openapi.json           # especificação OpenAPI exportada
```

## Algoritmos e complexidades

- **Kruskal:** ordena as arestas por `(peso, u, v)` e aceita as que ligam
  componentes diferentes, usando **Union-Find** com compressão de caminho e
  união por tamanho. Tempo `O(E log E)`; espaço `O(V + E)`.
- **Prim:** cresce uma árvore a partir de um vértice, retirando da fronteira a
  aresta de menor peso com **heap binário** e descarte preguiçoso de entradas
  obsoletas. Tempo `O(E log V)`; espaço `O(V + E)`. Em grafo desconexo,
  reinicia em cada componente para produzir a floresta.
- A **verificação** é independente dos algoritmos: confere `n − c` arestas,
  ausência de ciclos e a **propriedade do ciclo** (para toda aresta fora da
  árvore, seu peso é maior ou igual ao maior peso no caminho entre os extremos
  dentro da árvore).
- Com pesos distintos, a AGM é única. Com empates, pode haver várias AGMs de
  mesmo custo; o sistema explica e mostra as arestas que diferem.

## Decisões e transparência

- O frontend usa **Vue 3 + Vite + TypeScript**, com autorização do usuário. O
  motivo, a arquitetura e as consequências (Node apenas no desenvolvimento;
  `frontend/dist` versionado) estão em
  [`docs/FRONTEND_PIMP.md`](docs/FRONTEND_PIMP.md).
- O registro de uso de ferramentas de IA, incluindo decisões e divergências de
  dados, está em [`docs/AI_USAGE_LOG.md`](docs/AI_USAGE_LOG.md).
- Divergências encontradas em relação ao plano original: a planilha tem **199**
  linhas interestaduais (não 200), **71** pares únicos com divisa menor que
  0,5 km (não 142 linhas dirigidas) e o catálogo de coordenadas baixado tem
  **5.571** municípios no Brasil, mas São Paulo continua com **645**.

## Licença e uso

Projeto acadêmico da disciplina de Teoria dos Grafos. Os dados do IBGE são
públicos e referenciais; o arquivo de coordenadas do repositório
`kelvins/municipios-brasileiros` é distribuído sob licença MIT. Consulte
[`data/FONTES.md`](data/FONTES.md).
