# Exemplos de arquivos

Arquivos para testar a aba **Arquivo** do sistema. Todos também podem ser
usados na API em `POST /api/graph/upload`.

| Arquivo | O que demonstra |
|---|---|
| `grafo_valido.csv` | Grafo pequeno e conexo no formato `origem,destino,peso`. A MST tem custo 13. |
| `grafo_valido.json` | Grafo com nomes e coordenadas, desenhado na posição geográfica. |
| `grafo_desconexo.csv` | Duas componentes separadas. O sistema calcula uma floresta e avisa. |
| `grafo_com_avisos.csv` | Contém laço (`A,A`), aresta duplicada (`A,B` e `B,A`) e um peso maior na duplicata. O sistema mantém a menor e avisa. |
| `grafo_pesos_negativos.csv` | Pesos negativos. São aceitos, com aviso de que não fazem sentido no domínio de distâncias. |
| `grafo_peso_invalido.csv` | Erro de validação no peso `abc`, com o número da linha na mensagem. |
| `grafo_coluna_ausente.csv` | Cabeçalho sem a coluna de peso; erro legível. |
| `grafo_json_invalido.json` | JSON malformado; erro com linha e coluna. |

Formatos aceitos:

- **CSV**: cabeçalho `origem,destino,peso` ou `source,target,weight`, separador
  `,` ou `;`, ponto ou vírgula decimal.
- **JSON**: objeto com `nodes` (opcional) e `edges`; cada aresta usa
  `source`/`target` (ou `u`/`v`) e `weight` (ou `peso`).
