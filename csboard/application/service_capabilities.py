"""Safe interpretation of a service's declared capabilities.

``ServiceDefinition.capability`` remains the primary, persisted capability.
The optional ``config.capabilities`` array is a backwards-compatible extension
used only when it is a list containing non-empty strings. Nothing else in a
service config is capability metadata.
"""

from __future__ import annotations

from typing import Any


def declared_capabilities(service: Any) -> tuple[str, ...]:
    """Return the primary capability plus safe, de-duplicated secondaries."""
    values: list[str] = []
    primary = getattr(service, "capability", None)
    if isinstance(primary, str) and primary.strip():
        values.append(primary.strip())

    config = getattr(service, "config", None)
    secondary = config.get("capabilities") if isinstance(config, dict) else None
    if isinstance(secondary, list):
        values.extend(
            value.strip()
            for value in secondary
            if isinstance(value, str) and value.strip()
        )

    return tuple(dict.fromkeys(values))


def normalized_capability(capability: str) -> str:
    """Map legacy capability spelling to the runtime capability vocabulary."""
    return "speech_synthesis" if capability == "audio_generation" else capability


def supports_capability(service: Any, requested: str) -> bool:
    """Whether a service safely declares the requested runtime capability."""
    expected = normalized_capability(requested)
    return any(
        normalized_capability(value) == expected
        for value in declared_capabilities(service)
    )
