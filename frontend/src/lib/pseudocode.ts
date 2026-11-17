export const KRUSKAL_PSEUDOCODE = [
  'A ← ∅',
  'para cada vértice v: MAKE-SET(v)',
  'ordene E por peso crescente',
  'para cada aresta (u, v) em E:',
  '  se FIND-SET(u) ≠ FIND-SET(v):',
  '    A ← A ∪ {(u, v)}',
  '    UNION(u, v)',
  '    se |A| = |V| − 1: pare',
  'retorne A',
]

export const PRIM_PSEUDOCODE = [
  'para cada v: chave[v] ← ∞; pai[v] ← NULO',
  'chave[r] ← 0; Q ← fila de prioridade',
  'enquanto Q não vazia:',
  '  u ← EXTRAI-MÍNIMO(Q)',
  '  para cada vizinho v de u:',
  '    se v ∉ árvore e w(u, v) < chave[v]:',
  '      pai[v] ← u; chave[v] ← w(u, v)',
  'A ← {(pai[v], v) : v ≠ r}',
  'retorne A',
]
