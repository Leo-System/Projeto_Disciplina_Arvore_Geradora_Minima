"""Aplicação FastAPI: rotas, tratamento de erros e arquivos estáticos."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.routes import router
from .api.schemas import ErrorResponse, HealthResponse
from .algorithms.graph import GraphValidationError
from .data_loader import PROJECT_ROOT, DataLoadError
from .errors import DomainError

logger = logging.getLogger(__name__)

DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(
    title="Árvore Geradora Mínima — Municípios de São Paulo",
    version="1.0.0",
    description=(
        "Sistema web local que modela a malha de municípios de São Paulo como "
        "grafo ponderado e calcula a árvore geradora mínima com Prim e Kruskal, "
        "ambos implementados do zero."
    ),
    # A especificação OpenAPI fica em /openapi.json (e em docs/openapi.json).
    # O Swagger UI em /docs carrega os assets padrão via CDN.
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adiciona cabeçalhos de segurança básicos (PLAN §3.1) a todas as respostas."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    return response


app.include_router(router)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error={"code": code, "message": message, "details": details or []}
    )
    return JSONResponse(
        status_code=status_code, content=payload.model_dump(), headers=headers
    )


# Códigos de erro da API mapeados para códigos de status HTTP padrão.
_STATUS_PARA_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    return _error_response(
        error.status_code, error.code, error.message, error.details
    )


@app.exception_handler(GraphValidationError)
async def handle_graph_error(request: Request, error: GraphValidationError) -> JSONResponse:
    return _error_response(422, "VALIDATION_ERROR", str(error))


@app.exception_handler(RequestValidationError)
async def handle_request_validation(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    details = []
    for item in error.errors():
        message = str(item.get("msg", "Valor inválido")).removeprefix("Value error, ")
        location = ".".join(str(part) for part in item.get("loc", []))
        details.append(f"{location}: {message}" if location else message)
    return _error_response(
        422,
        "VALIDATION_ERROR",
        "Dados de entrada inválidos.",
        details,
    )


@app.exception_handler(StarletteHTTPException)
async def handle_starlette_http_error(
    request: Request, error: StarletteHTTPException
) -> JSONResponse:
    """Converte erros HTTP padrão do Starlette/FastAPI para o envelope da API.

    Garante que 404/405 (e demais códigos) retornem
    {"error": {"code", "message", "details"}} em vez do formato próprio do
    Starlette. Cabeçalhos originais (ex.: ``Allow`` no 405) são preservados
    e nenhum stack trace vaza para o cliente.
    """
    code = _STATUS_PARA_CODE.get(error.status_code, "HTTP_ERROR")
    message = str(error.detail) if error.detail is not None else ""
    return _error_response(
        error.status_code,
        code,
        message,
        [],
        headers=dict(error.headers or {}),
    )


@app.exception_handler(DataLoadError)
async def handle_data_error(request: Request, error: DataLoadError) -> JSONResponse:
    logger.error("Falha ao carregar dados: %s", error)
    return _error_response(500, "DATA_ERROR", str(error))


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Erro inesperado em %s", request.url.path)
    return _error_response(
        500,
        "INTERNAL_ERROR",
        "Erro interno inesperado. Consulte o terminal do servidor para detalhes.",
    )


@app.get("/health", response_model=HealthResponse, tags=["infraestrutura"])
def health() -> dict[str, str]:
    """Verificação simples de que o servidor está no ar."""
    return {"status": "ok"}


@app.get("/api/health", response_model=HealthResponse, include_in_schema=False)
def api_health() -> dict[str, str]:
    return {"status": "ok"}


if DIST_DIR.exists():
    # O frontend compilado é servido na raiz. As rotas /api e /docs são
    # registradas antes, portanto continuam tendo prioridade.
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def frontend_missing() -> str:
        return """
        <!doctype html>
        <html lang="pt-BR">
          <head><meta charset="utf-8"><title>Frontend não compilado</title></head>
          <body style="font-family: sans-serif; max-width: 720px; margin: 3rem auto;">
            <h1>Frontend ainda não compilado</h1>
            <p>Compile a interface com:</p>
            <pre>cd frontend
npm install
npm run build</pre>
            <p>Ou rode o modo de desenvolvimento com <code>npm run dev</code>.</p>
            <p>A especificação da API está em <a href="/openapi.json">/openapi.json</a>.</p>
          </body>
        </html>
        """
