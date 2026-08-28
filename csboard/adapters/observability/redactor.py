from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|authorization|cookie|secret|password|token|access[_-]?token|refresh[_-]?token)$", re.I)
_BEARER = re.compile(r"(?i)(bearer\s+)[^\s]+")
_QUERY_SECRET = re.compile(r"(?i)([?&](?:api[_-]?key|token|secret|password)=)[^&#\s]+")


class DefaultRedactor:
    """Redacts credentials before diagnostics reach disk or an export bundle."""

    def __init__(self, paths: dict[Path, str] | None = None) -> None:
        self.paths = {path.resolve(): label for path, label in (paths or {}).items()}

    def redact(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {
                str(key): "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else self.redact(value)
                for key, value in payload.items()
            }
        if isinstance(payload, list):
            return [self.redact(item) for item in payload]
        if isinstance(payload, tuple):
            return [self.redact(item) for item in payload]
        if isinstance(payload, str):
            value = _BEARER.sub(r"\1[REDACTED]", payload)
            value = _QUERY_SECRET.sub(r"\1[REDACTED]", value)
            for path, label in self.paths.items():
                value = value.replace(str(path), label)
            return value[:4096]
        return payload
