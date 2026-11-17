"""Sobe o servidor local e imprime a URL da aplicação.

Uso:
    python run.py
    python run.py --port 8080 --no-browser
"""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor local do projeto de AGM.")
    parser.add_argument("--host", default="127.0.0.1", help="Endereço de escuta.")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Não abrir o navegador automaticamente.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Recarregar o servidor ao alterar arquivos (desenvolvimento).",
    )
    args = parser.parse_args()

    # Garante que os caminhos relativos do projeto funcionem de qualquer lugar.
    os.chdir(PROJECT_ROOT)

    url = f"http://{args.host}:{args.port}"
    print("=" * 60)
    print("Árvore Geradora Mínima — Municípios de São Paulo")
    print(f"Aplicação: {url}")
    print(f"Especificação OpenAPI: {url}/openapi.json")
    print(f"Documentação interativa: {url}/docs")
    print("=" * 60)

    if not DIST_DIR.exists():
        print(
            "Aviso: frontend/dist não encontrado. Compile a interface com "
            "'cd frontend && npm install && npm run build', ou use o modo de "
            "desenvolvimento do Vite."
        )

    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
