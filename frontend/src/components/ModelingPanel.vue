<template>
  <article class="prose">
    <h3>Modelagem do grafo</h3>
    <dl class="concept-list">
      <div>
        <dt>Vértices</dt>
        <dd>
          Municípios do estado de São Paulo, identificados pelo
          <strong>código IBGE de 7 dígitos</strong>. Cada vértice tem nome, latitude e longitude da
          sede.
        </dd>
      </div>
      <div>
        <dt>Arestas</dt>
        <dd>
          Par de municípios <strong>vizinhos</strong>, isto é, que fazem divisa: é possível sair de
          um e chegar ao outro sem passar por município intermediário. A origem principal é a
          planilha <em>Municípios Limítrofes</em> do IBGE (<code>source = divisa</code>). Exceções
          documentadas ficam em <code>data/manual/extras.csv</code> (<code>source = manual</code>);
          hoje há uma: Ilhabela ↔ São Sebastião (balsa).
        </dd>
      </div>
      <div>
        <dt>Tipo</dt>
        <dd>
          <strong>Não direcionado</strong>, <strong>ponderado</strong> e
          <strong>simples</strong> (sem laços e sem arestas paralelas).
        </dd>
      </div>
      <div>
        <dt>Peso</dt>
        <dd>
          Distância em km entre as sedes dos dois municípios pela
          <strong>fórmula de Haversine</strong> (raio da Terra = 6.371,0088 km). Interpretação:
          aproximação do custo de lançar uma ligação entre os municípios.
        </dd>
      </div>
      <div>
        <dt>Atributos extras da aresta</dt>
        <dd>
          <code>border_km</code>: extensão da divisa no IBGE; <code>source</code>:
          <code>divisa</code> ou <code>manual</code>; <code>short_border</code>: verdadeiro quando a
          divisa tem menos de 0,5 km (contato praticamente pontual). Nenhum deles altera o peso.
        </dd>
      </div>
    </dl>

    <h3>Hipóteses e limitações</h3>
    <ol class="limitations-list">
      <li>
        A distância em linha reta entre sedes <strong>não</strong> é a distância por rodovia. O
        custo real dependeria de relevo, faixa de domínio, desapropriações e outros fatores.
      </li>
      <li>
        A vizinhança vem da malha municipal 2024 do IBGE. Os próprios dados do IBGE são
        referenciais, com finalidade estatística.
      </li>
      <li>
        Divisas muito curtas (<code>short_border</code>) são mantidas, pois o município toca o outro
        sem intermediário. Isso é uma decisão do projeto, não um fato absoluto.
      </li>
      <li>
        Municípios fora da seleção do usuário são ignorados: o grafo é o
        <strong>subgrafo induzido</strong> pela seleção.
      </li>
      <li>
        Se o grafo for <strong>desconexo</strong>, não existe árvore geradora. O sistema calcula a
        <strong>floresta geradora mínima</strong> (uma AGM por componente) e avisa.
      </li>
      <li>
        Três nomes divergem entre as fontes (Biritiba Mirim, Florínea e Itaoca). A junção é sempre
        feita pelo <strong>código IBGE</strong>, nunca pelo nome; a grafia exibida é a da planilha
        do IBGE.
      </li>
    </ol>

    <h3>Dados</h3>
    <p>
      Malha municipal 2024 do IBGE (<em>Municípios Limítrofes</em>) e coordenadas das sedes do
      repositório <code>kelvins/municipios-brasileiros</code> (licença MIT). A preparação é feita
      por <code>scripts/build_dataset.py</code> e o sistema em execução lê apenas
      <code>data/processed/</code>. Consulte <code>data/FONTES.md</code> para origem, data de
      download e limitações.
    </p>
  </article>
</template>
