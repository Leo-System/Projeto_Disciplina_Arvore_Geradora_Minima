"""Leitura e validação de grafos enviados pelo usuário (CSV ou JSON).

Formatos aceitos (seção 10.3 do plano):

CSV — lista de arestas::

    origem,destino,peso
    A,B,12.5

Também são aceitos ``source,target,weight`` e separador ``;``.

JSON::

    {
      "nodes": [{"id": "A", "name": "Opcional", "lat": -22.3, "lon": -49.0}],
      "edges": [{"source": "A", "target": "B", "weight": 12.5}]
    }
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
from dataclasses import dataclass
from typing import Any

from ..algorithms.graph import Graph, GraphValidationError
from ..errors import PayloadTooLargeError, ValidationError

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "5242880"))
MAX_EDGES = int(os.getenv("MAX_EDGES", "200000"))

_ORIGIN_NAMES = {"origem", "source", "from", "u"}
_DESTINATION_NAMES = {"destino", "target", "to", "v"}
_WEIGHT_NAMES = {"peso", "weight", "custo", "cost", "w"}


@dataclass(frozen=True)
class ParsedGraph:
    graph: Graph
    warnings: list[str]
    discarded: list[dict[str, str]]


def _parse_number(raw: str, context: str) -> float:
    """Converte números com ponto ou vírgula decimal."""
    value = raw.strip()
    if not value:
        raise ValidationError(f"Peso vazio {context}.")
    if "," in value and "." in value:
        # Formato brasileiro com separador de milhar: 1.234,5
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValidationError(f"Peso inválido {context}: {raw!r}.") from exc
    if not math.isfinite(number):
        raise ValidationError(f"Peso não finito {context}: {raw!r}.")
    return number


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            "O arquivo precisa estar codificado em UTF-8."
        ) from exc


def _detect_format(filename: str, text: str) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "json":
        return "json"
    if suffix == "csv":
        return "csv"
    if text.lstrip().startswith("{"):
        return "json"
    return "csv"


def _column_index(header: list[str], aliases: set[str], label: str) -> int:
    for index, name in enumerate(header):
        if name in aliases:
            return index
    raise ValidationError(
        f"Coluna de {label} não encontrada no cabeçalho CSV. "
        "Use origem,destino,peso (ou source,target,weight)."
    )


def _parse_csv(text: str) -> ParsedGraph:
    lines = text.splitlines()
    if not lines:
        raise ValidationError("O arquivo CSV está vazio.")

    first_line = lines[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValidationError("O arquivo CSV está vazio.") from exc

    normalized_header = [
        name.strip().lower().lstrip("\ufeff") for name in header
    ]
    origin_index = _column_index(normalized_header, _ORIGIN_NAMES, "origem")
    destination_index = _column_index(
        normalized_header, _DESTINATION_NAMES, "destino"
    )
    weight_index = _column_index(normalized_header, _WEIGHT_NAMES, "peso")

    edge_records: list[dict[str, Any]] = []
    node_ids: list[str] = []
    seen_nodes: set[str] = set()
    errors: list[str] = []

    for line_number, row in enumerate(reader, start=2):
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) <= max(origin_index, destination_index, weight_index):
            errors.append(
                f"Linha {line_number}: esperadas {len(header)} colunas, "
                f"encontradas {len(row)}."
            )
            continue
        origin = row[origin_index].strip()
        destination = row[destination_index].strip()
        if not origin or not destination:
            errors.append(
                f"Linha {line_number}: origem e destino não podem ser vazios."
            )
            continue
        try:
            weight = _parse_number(row[weight_index], f"na linha {line_number}")
        except ValidationError as error:
            errors.append(str(error))
            continue
        edge_records.append(
            {"u": origin, "v": destination, "weight": weight, "attrs": {}}
        )
        for node_id in (origin, destination):
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                node_ids.append(node_id)

    if len(edge_records) > MAX_EDGES:
        raise PayloadTooLargeError(
            f"O arquivo tem {len(edge_records)} arestas; o limite é {MAX_EDGES}."
        )
    if errors:
        details = errors[:20]
        if len(errors) > len(details):
            details.append(f"... e mais {len(errors) - len(details)} erro(s).")
        raise ValidationError("O CSV contém erros de validação.", details=details)
    if not edge_records:
        raise ValidationError("O CSV não contém nenhuma aresta de dados.")

    nodes = [{"id": node_id, "name": node_id} for node_id in node_ids]
    try:
        graph = Graph.from_records(nodes, edge_records)
    except GraphValidationError as error:
        raise ValidationError(str(error)) from error
    return ParsedGraph(graph=graph, warnings=list(graph.warnings), discarded=[])


def _json_endpoint(edge: dict[str, Any]) -> tuple[str, str]:
    origin = edge.get("source", edge.get("u", edge.get("origem")))
    destination = edge.get("target", edge.get("v", edge.get("destino")))
    return origin, destination


def _parse_json(text: str) -> ParsedGraph:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"JSON inválido na linha {exc.lineno}, coluna {exc.colno}: {exc.msg}."
        ) from exc
    if not isinstance(payload, dict):
        raise ValidationError(
            "O JSON deve ser um objeto com as chaves 'nodes' (opcional) e 'edges'."
        )

    raw_nodes = payload.get("nodes", [])
    raw_edges = payload.get("edges")
    if raw_edges is None:
        raise ValidationError("O JSON precisa da chave 'edges' com a lista de arestas.")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValidationError("'nodes' e 'edges' devem ser listas.")
    if len(raw_edges) > MAX_EDGES:
        raise PayloadTooLargeError(
            f"O arquivo tem {len(raw_edges)} arestas; o limite é {MAX_EDGES}."
        )

    nodes: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            raise ValidationError(f"O nó de índice {index} não é um objeto.")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValidationError(f"O nó de índice {index} não tem 'id' válido.")
        node_id = node_id.strip()
        if node_id in seen_nodes:
            raise ValidationError(f"Vértice duplicado no JSON: {node_id}.")
        seen_nodes.add(node_id)
        latitude = node.get("lat", node.get("latitude"))
        longitude = node.get("lon", node.get("longitude"))
        nodes.append(
            {
                "id": node_id,
                "name": node.get("name", node_id),
                "lat": latitude,
                "lon": longitude,
            }
        )

    edge_records: list[dict[str, Any]] = []
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            raise ValidationError(f"A aresta de índice {index} não é um objeto.")
        origin, destination = _json_endpoint(edge)
        if not isinstance(origin, str) or not isinstance(destination, str):
            raise ValidationError(
                f"A aresta de índice {index} precisa de 'source' e 'target' "
                "(ou 'u' e 'v')."
            )
        weight = edge.get("weight", edge.get("peso"))
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            raise ValidationError(
                f"O peso da aresta de índice {index} não é um número: {weight!r}."
            )
        edge_records.append(
            {
                "u": origin.strip(),
                "v": destination.strip(),
                "weight": float(weight),
                "attrs": {},
            }
        )
        for node_id in (origin.strip(), destination.strip()):
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({"id": node_id, "name": node_id})

    if not nodes and not edge_records:
        raise ValidationError("O JSON não contém vértices nem arestas.")

    try:
        graph = Graph.from_records(nodes, edge_records)
    except GraphValidationError as error:
        raise ValidationError(str(error)) from error
    return ParsedGraph(graph=graph, warnings=list(graph.warnings), discarded=[])


def parse_upload(filename: str, content: bytes) -> ParsedGraph:
    """Valida tamanho, codificação e formato; devolve grafo e avisos."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(
            "O arquivo excede o limite de 5 MB. "
            "Envie um grafo menor ou divida os dados."
        )
    if not content.strip():
        raise ValidationError("O arquivo enviado está vazio.")

    text = _decode(content)
    file_format = _detect_format(filename, text)
    if file_format == "json":
        return _parse_json(text)
    return _parse_csv(text)
