"""Fixtures e utilitários compartilhados pelos testes de especificação.

Os testes desta pasta foram escritos antes da implementação e usam apenas o
contrato público descrito para os módulos de grafo, Prim, Kruskal e verificação.
"""

from __future__ import annotations

import copy
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import networkx as nx
import pytest

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_DO_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_DO_PROJETO))

from backend.app.algorithms.graph import Graph  # noqa: E402


# ---------------------------------------------------------------------------
# Construtores de registros usados por Graph.from_records
# ---------------------------------------------------------------------------


def no(id_, name=None, lat=None, lon=None):
    """Cria o registro de um vértice no formato aceito por from_records."""
    return {"id": id_, "name": name, "lat": lat, "lon": lon}


def aresta(u, v, weight, attrs=None):
    """Cria o registro de uma aresta no formato aceito por from_records."""
    return {
        "u": u,
        "v": v,
        "weight": weight,
        "attrs": {} if attrs is None else dict(attrs),
    }


def construir_grafo(nodes, edges):
    return Graph.from_records(nodes, edges)


def construir_grafo_classico():
    """Grafo clássico A-F cuja árvore geradora mínima custa 13."""
    nodes = [no(v) for v in "ABCDEF"]
    edges = [
        aresta("A", "B", 4),
        aresta("A", "C", 2),
        aresta("B", "C", 1),
        aresta("B", "D", 5),
        aresta("C", "D", 8),
        aresta("C", "E", 10),
        aresta("D", "E", 2),
        aresta("D", "F", 6),
        aresta("E", "F", 3),
    ]
    return construir_grafo(nodes, edges)


def construir_grafo_desconexo():
    """Três componentes: {A, B}, {C, D} e o vértice isolado E."""
    nodes = [no(v) for v in "ABCDE"]
    edges = [
        aresta("A", "B", 1),
        aresta("C", "D", 2),
    ]
    return construir_grafo(nodes, edges)


def construir_grafo_com_empates():
    """Ciclo de quatro vértices com todas as arestas de mesmo peso."""
    nodes = [no(v) for v in "ABCD"]
    edges = [
        aresta("A", "B", 1),
        aresta("B", "C", 1),
        aresta("C", "D", 1),
        aresta("D", "A", 1),
    ]
    return construir_grafo(nodes, edges)


def construir_grafo_com_pesos_negativos():
    """Grafo pequeno cuja única MST tem custo -8."""
    nodes = [no(v) for v in "ABCD"]
    edges = [
        aresta("A", "B", -5),
        aresta("B", "C", -2),
        aresta("C", "D", -1),
        aresta("A", "D", 10),
        aresta("B", "D", 3),
    ]
    return construir_grafo(nodes, edges)


# ---------------------------------------------------------------------------
# Leitura tolerante de arestas e eventos do contrato público
# ---------------------------------------------------------------------------


def _extrair(objeto, nomes, descricao):
    if isinstance(objeto, dict):
        for nome in nomes:
            if nome in objeto:
                return objeto[nome]
    for nome in nomes:
        if hasattr(objeto, nome):
            return getattr(objeto, nome)
    raise AssertionError(f"Não foi possível ler {descricao} de {objeto!r}")


def extremidades(edge):
    """Devolve (u, v) de uma Edge ou de um dicionário equivalente."""
    return (
        _extrair(edge, ("u", "source"), "a extremidade u"),
        _extrair(edge, ("v", "target"), "a extremidade v"),
    )


def peso_da_aresta(edge):
    return float(_extrair(edge, ("weight",), "o peso da aresta"))


def aresta_normalizada(edge):
    u, v = extremidades(edge)
    if u > v:
        u, v = v, u
    return (u, v, peso_da_aresta(edge))


def conjunto_de_arestas(resultado):
    """Representação determinística e não orientada das arestas do resultado."""
    return sorted(aresta_normalizada(e) for e in resultado.edges)


def custo_das_arestas(arestas):
    return sum(peso_da_aresta(e) for e in arestas)


def achar_aresta(graph, u, v):
    """Localiza a aresta {u, v} no grafo, independentemente da orientação."""
    for edge in graph.edges:
        a, b = extremidades(edge)
        if {a, b} == {u, v}:
            return edge
    raise AssertionError(f"A aresta {{{u}, {v}}} não existe no grafo")


def tipo_evento(evento):
    return _extrair(evento, ("type",), "o tipo do evento")


def campo_evento(evento, nome):
    return _extrair(evento, (nome,), f"o campo {nome!r} do evento")


# ---------------------------------------------------------------------------
# Geração determinística de grafos e comparação com NetworkX
# ---------------------------------------------------------------------------


def para_networkx(nodes, edges):
    grafo = nx.Graph()
    for node in nodes:
        grafo.add_node(node["id"])
    for edge in edges:
        grafo.add_edge(edge["u"], edge["v"], weight=edge["weight"])
    return grafo


def custo_mst_networkx(grafo_nx):
    mst = nx.minimum_spanning_tree(grafo_nx, weight="weight")
    return float(sum(dados["weight"] for _, _, dados in mst.edges(data=True)))


def gerar_grafo_conexo(n, extras, seed, pesos_negativos=False):
    """Gera um grafo conexo: primeiro uma árvore aleatória, depois extras.

    Retorna (Graph, networkx.Graph) para permitir comparar os custos.
    """
    rnd = random.Random(seed)
    ids = [f"V{i:03d}" for i in range(n)]
    nodes = [no(i) for i in ids]
    edges = []
    vistos = set()

    def sortear_peso():
        if pesos_negativos:
            return float(rnd.randint(-9, 20))
        return float(rnd.randint(1, 25))

    # Árvore aleatória: garante conectividade.
    for i in range(1, n):
        j = rnd.randrange(i)
        u, v = ids[j], ids[i]
        edges.append(aresta(u, v, sortear_peso()))
        vistos.add((min(u, v), max(u, v)))

    # Arestas extras, sem laços nem duplicatas.
    maximo_extras = n * (n - 1) // 2 - (n - 1)
    extras = min(extras, maximo_extras)
    tentativas = 0
    while len(edges) < (n - 1) + extras and tentativas < 100 * (extras + 1):
        tentativas += 1
        u, v = rnd.sample(ids, 2)
        chave = (min(u, v), max(u, v))
        if chave in vistos:
            continue
        vistos.add(chave)
        edges.append(aresta(u, v, sortear_peso()))

    grafo = construir_grafo(nodes, edges)
    return grafo, para_networkx(nodes, edges)


# ---------------------------------------------------------------------------
# Apoio para testar a verificação com resultados deliberadamente inválidos
# ---------------------------------------------------------------------------


def resultado_com_arestas(resultado, novas_arestas):
    """Cria uma cópia do resultado trocando apenas a lista de arestas."""
    novas = list(novas_arestas)
    novo_custo = custo_das_arestas(novas)

    try:
        clone = copy.copy(resultado)
        clone.edges = novas
        clone.total_cost = novo_custo
        return clone
    except Exception:
        return SimpleNamespace(
            algorithm=getattr(resultado, "algorithm", "teste"),
            edges=novas,
            total_cost=novo_custo,
            n_components=getattr(resultado, "n_components", 1),
            components=getattr(resultado, "components", None),
            is_forest=getattr(resultado, "is_forest", True),
            metrics=dict(getattr(resultado, "metrics", {})),
            trace=None,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def grafo_classico():
    return construir_grafo_classico()


@pytest.fixture
def grafo_desconexo():
    return construir_grafo_desconexo()


@pytest.fixture
def grafo_com_empates():
    return construir_grafo_com_empates()


@pytest.fixture
def grafo_com_pesos_negativos():
    return construir_grafo_com_pesos_negativos()
