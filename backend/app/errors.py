"""Erros de domínio traduzidos para respostas HTTP pela API."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Erro esperado, com mensagem legível para o usuário final."""

    status_code = 400
    code = "DOMAIN_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: list[Any] | None = None,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(DomainError):
    status_code = 422
    code = "VALIDATION_ERROR"


class PayloadTooLargeError(DomainError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"
