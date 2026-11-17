# Registro de uso de IA

Registro de transparência exigido pela disciplina. Cada linha indica a data, a
ferramenta ou agente, a tarefa realizada e os arquivos afetados. O registro é
**somente acrescentado**: correções posteriores entram como novas linhas.

| Data | Ferramenta / agente | Tarefa | Arquivos afetados |
|---|---|---|---|
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Leitura do plano, das instruções do professor e das diretrizes; levantamento de requisitos e decisões iniciais | `.sdd/PLAN.md`, `.opencode/*` (somente leitura) |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Conferência dos dados brutos, definição dos fatos de validação e implementação do pipeline de preparação | `scripts/build_dataset.py`, `data/processed/*`, `data/manual/extras.csv` |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Implementação do grafo, Union-Find, Kruskal, Prim, resultado e verificação independente | `backend/app/algorithms/*` |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Implementação dos serviços de dados, presets, seleção, upload, execução, serialização e benchmark | `backend/app/services/*`, `backend/app/data_loader.py` |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Implementação da API FastAPI, esquemas Pydantic, tratamento de erros e arquivos estáticos | `backend/app/api/*`, `backend/app/main.py`, `backend/app/errors.py` |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Implementação da interface Vue 3 com Vite e TypeScript: canvas, painéis, passo a passo, comparação, benchmark e conteúdo teórico | `frontend/src/*`, `frontend/package.json`, `frontend/vite.config.ts` |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Verificação da interface servida pelo FastAPI com Playwright (navegador Chromium headless): carregamento inicial, abas, passo a passo, comparação, benchmark e layout móvel | Nenhum arquivo do projeto (script temporário em `/tmp/opencode`) |
| 08/11/2026 | OpenCode com `opencode/deepseek-v4.1-flash-free` (agente principal) | Redação dos exemplos de upload, fontes dos dados e documentação do frontend | `examples/*`, `data/FONTES.md`, `docs/FRONTEND_PIMP.md` |

## Decisões registradas

- **08/11/2026 — Frontend:** adotado Vue 3 + Vite + TypeScript no lugar de
  JavaScript puro, com autorização do usuário. O build é feito com Node e o
  resultado é versionado em `frontend/dist`, que o FastAPI serve. Justificativa
  e consequências em `docs/FRONTEND_PIMP.md`.
- **08/11/2026 — Dados:** a planilha do IBGE tem 3.864 linhas com origem em SP:
  3.664 pares SP–SP, **199** linhas com vizinho de outro estado e 1 linha vazia
  (Ilhabela). O plano citava 200 interestaduais; a contagem real foi conferida
  nos arquivos e é 199.
- **08/11/2026 — Dados:** há **71 pares únicos** com divisa menor que 0,5 km,
  incluindo **54 pares** com `COMP_KM = 0`. O plano citava 54 e 142,
  respectivamente; 142 é o número de linhas dirigidas antes da deduplicação.
- **08/11/2026 — Dados:** o `municipios.csv` baixado tem **5.571** municípios
  no Brasil (inclui Boa Esperança do Norte, 5101837). O filtro por São Paulo
  continua resultando em **645** municípios.
- **08/11/2026 — Grafia:** quando os arquivos divergem, a junção é sempre pelo
  código IBGE e a grafia exibida é a da planilha do IBGE (`Biritiba Mirim`,
  `Florínea`, `Itaoca`).
- **08/11/2026 — Biblioteca de grafos:** nenhuma biblioteca de grafos no código
  de execução. NetworkX é usado somente em `tests/`, para conferir custos.
- **08/11/2026 — Dependência de Node:** Node é necessário apenas para
  desenvolver ou recompilar o frontend. Na apresentação, `python run.py` serve
  o conteúdo já compilado de `frontend/dist`, sem Node e sem internet.
