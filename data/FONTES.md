# Fontes dos dados

Este documento registra a origem, a data de download, a versão e as limitações
dos dados usados pelo projeto. O sistema em execução lê **apenas**
`data/processed/`; os arquivos brutos em `data/raw/` servem para regenerar os
dados processados.

## Arquivos de entrada

| Arquivo | Origem | Conteúdo | Data do download | Versão |
|---|---|---|---|---|
| `data/raw/BR_Municipios_2024_LIMITROFES.ods` | IBGE — [Municípios Limítrofes](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/42224-municipios-limitrofes.html) | Aba `Municípios Limítrofes`: relações de divisa entre municípios, com a extensão da divisa em km (`COMP_KM`) | 08/11/2026 | 2024 |
| `data/raw/municipios.csv` | GitHub [`kelvins/municipios-brasileiros`](https://github.com/kelvins/municipios-brasileiros) | Coordenadas das sedes municipais, código IBGE, UF e outros campos | 08/11/2026 | commit baixado em 08/11/2026 |

O arquivo de coordenadas é distribuído sob licença **MIT**. O arquivo do IBGE é
de origem pública; a licença não é declarada dentro do arquivo baixado. O uso
neste projeto é acadêmico. Consulte os termos de uso do IBGE no portal oficial.

## Arquivos processados (versionados)

- `data/processed/cities.csv`: 645 municípios de São Paulo, com `id` (código
  IBGE de 7 dígitos), `name`, `lat` e `lon`.
- `data/processed/edges.csv`: 1.833 arestas. Destas, 1.832 vêm de divisas do
  IBGE (`source = divisa`) e 1 é uma ligação manual documentada
  (`source = manual`): Ilhabela ↔ São Sebastião, por balsa.
- `data/manual/extras.csv`: ligações que não são divisa terrestre. Hoje contém
  apenas a travessia por balsa entre Ilhabela e São Sebastião. A distância é
  calculada pelo mesmo método das demais arestas.

## Preparação

O script `scripts/build_dataset.py` lê os arquivos brutos, filtra São Paulo
(`codigo_uf == 35`), junta coordenadas **pelo código IBGE** (nunca pelo nome),
calcula a distância de Haversine com raio da Terra de 6.371,0088 km, incorpora
as ligações manuais e grava os arquivos processados. Ele também valida os fatos
abaixo e falha com mensagem clara se algo divergir:

- 645 municípios paulistas nos dois arquivos;
- 3.864 linhas com origem em SP na planilha do IBGE;
- 3.664 linhas SP–SP, 199 linhas com vizinho de outro estado e 1 linha vazia
  (Ilhabela);
- 1.832 pares únicos de divisa SP–SP após deduplicação;
- apenas Ilhabela isolada no grafo de divisas;
- 54 pares com `COMP_KM = 0` e 71 pares com divisa menor que 0,5 km;
- três divergências de grafia entre as fontes (Biritiba Mirim, Florínea e
  Itaoca), resolvidas pelo código IBGE, exibindo a grafia da planilha do IBGE.

Para regenerar:

```bash
python scripts/build_dataset.py
```

## Limitações

- A distância é a **linha reta entre as sedes**, não a distância rodoviária. O
  custo real de uma ligação dependeria de relevo, faixa de domínio,
  desapropriações e outros fatores.
- A vizinhança vem da malha municipal de 2024 do IBGE. Os dados do IBGE são
  referenciais e têm finalidade estatística.
- Divisas muito curtas são mantidas: o município toca o outro sem município
  intermediário. É uma decisão do projeto, não um fato absoluto.
- A ligação por balsa é uma exceção manual. Sem ela, Ilhabela fica isolada no
  grafo de divisas terrestres.
- O arquivo de coordenadas do repositório `kelvins/municipios-brasileiros`
  contém 5.571 municípios do Brasil na versão baixada (inclui Boa Esperança do
  Norte, criada depois da versão anterior). O filtro por São Paulo continua
  resultando nos 645 municípios paulistas.
- Nenhum dado é completado de memória: divergências fazem o script de
  preparação falhar para serem investigadas.
