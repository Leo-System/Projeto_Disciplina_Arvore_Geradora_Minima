<template>
  <article class="prose">
    <h3>Árvore geradora mínima</h3>
    <p>
      Uma <strong>árvore geradora</strong> de um grafo conexo é um subgrafo que contém todos os
      vértices e é conexo e acíclico. Com <em>n</em> vértices, ela tem sempre
      <em>n − 1</em> arestas. A <strong>árvore geradora mínima (AGM)</strong> é a árvore geradora
      cuja soma dos pesos das arestas é a menor possível.
    </p>
    <p>
      Se todos os pesos forem distintos, a AGM é <strong>única</strong>. Com pesos empatados podem
      existir várias AGMs, mas todas têm o mesmo custo total. Pesos negativos não invalidam o
      problema, pois toda árvore geradora tem o mesmo número de arestas.
    </p>

    <h3>Por que o método guloso funciona</h3>
    <dl class="concept-list">
      <div>
        <dt>Propriedade do corte</dt>
        <dd>
          Um corte divide os vértices em dois conjuntos. Se um conjunto parcial de arestas não cruza
          o corte, a aresta de menor peso que cruza o corte é
          <strong>segura</strong>: existe alguma AGM que a contém.
        </dd>
      </div>
      <div>
        <dt>Propriedade do ciclo</dt>
        <dd>
          Em qualquer ciclo, uma aresta com peso estritamente maior que todas as outras do ciclo
          <strong>não pertence a nenhuma AGM</strong>. É por isso que rejeitar uma aresta que
          fecharia ciclo é seguro.
        </dd>
      </div>
      <div>
        <dt>Esquema genérico</dt>
        <dd>
          Os dois algoritmos começam com um conjunto vazio e acrescentam, passo a passo, uma aresta
          segura. Kruskal e Prim diferem apenas na forma de escolher essa aresta.
        </dd>
      </div>
    </dl>

    <h3>Kruskal</h3>
    <p>
      Ordena todas as arestas por peso crescente e aceita uma aresta somente se seus extremos
      estiverem em componentes diferentes. O <strong>Union-Find</strong>, com compressão de caminho
      e união por tamanho, faz essa verificação em tempo praticamente constante. O estado
      intermediário é uma floresta que vai se fundindo.
    </p>
    <p class="formula">Tempo: O(E log E) = O(E log V) · Espaço: O(V + E)</p>

    <h3>Prim</h3>
    <p>
      Cresce uma única árvore a partir de um vértice inicial. A cada passo retira da
      <strong>fronteira</strong> a aresta de menor peso que liga a árvore a um vértice ainda fora
      dela. Usando heap binário e descarte preguiçoso de entradas obsoletas, o custo é O(E log V). A
      variante com vetor e busca linear custa O(V²), mas não está implementada (apenas teórica/
      comparativa).
    </p>
    <p class="formula">
      Tempo com heap: O(E log V) · com vetor: O(V²) (teórico) · Espaço: O(V + E)
    </p>

    <h3>Esparso × denso</h3>
    <p>
      Kruskal tende a ser mais eficiente em grafos <strong>esparsos</strong>, em que E é próximo de
      V. Prim com vetor tende a se destacar em grafos <strong>densos</strong>, em que E se aproxima
      de V². Em grafos desconexos não existe uma única árvore geradora: os algoritmos produzem uma
      <strong>floresta geradora mínima</strong> com n − c arestas, em que c é o número de
      componentes.
    </p>

    <h3>AGM não é caminho mínimo</h3>
    <p>
      A AGM minimiza o custo total da estrutura, não a distância entre dois vértices específicos. O
      caminho entre dois vértices dentro da AGM não é necessariamente o caminho mais curto no grafo
      original; para isso existe o algoritmo de Dijkstra, que usa distância acumulada, e não o peso
      da aresta, como critério.
    </p>
  </article>
</template>
