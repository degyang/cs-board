"""Error Contract — 统一错误响应格式。"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from csboard.domain.errors import DomainError


def domain_error_response(
    exc: DomainError,
    status_code: int = 400,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """将 DomainError 转换为统一错误响应格式。"""
    body: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "unavailable": [],
            "details": details,
        }
    }
    return JSONResponse(content=body, status_code=status_code)
