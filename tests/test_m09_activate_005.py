"""Native capability-router activation-root wiring regression coverage."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from backend import mountain_capability_api
from tests.infographic_activation_fixture import create_root


class _CapturingCapabilities:
    def __init__(self, _registry, *, project_root, external_stage_gate) -> None:
        self.project_root = project_root
        self.external_stage_gate = external_stage_gate

    def snapshot(self) -> dict[str, object]:
        return {
            "root": str(self.project_root),
            "external_gate": self.external_stage_gate(),
        }


def _registry(data_dir: Path) -> FilesystemServiceRegistry:
    return FilesystemServiceRegistry(
        data_dir, PlaintextSecretStore(data_dir / ".secrets"),
    )


def _snapshot(router) -> dict[str, object]:
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/v1/capabilities")
    return asyncio.run(endpoint())


def test_router_uses_explicit_project_root_for_pointer_and_external_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_root = create_root(project_root)
    data_dir = tmp_path / "separate-runtime-data"
    monkeypatch.setattr(mountain_capability_api, "CapabilityService", _CapturingCapabilities)

    router = mountain_capability_api.mountain_capability_router(
        _registry(data_dir), project_root=project_root / ".",
    )

    assert _snapshot(router) == {
        "root": str(project_root.resolve()),
        "external_gate": True,
    }


@pytest.mark.parametrize("pointer", [None, "{not-json"])
def test_router_external_gate_fails_closed_for_missing_or_invalid_project_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pointer: str | None,
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_root = create_root(project_root)
    pointer_path = project_root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
    if pointer is None:
        pointer_path.unlink()
    else:
        pointer_path.write_text(pointer, encoding="utf-8")
    monkeypatch.setattr(mountain_capability_api, "CapabilityService", _CapturingCapabilities)

    router = mountain_capability_api.mountain_capability_router(
        _registry(tmp_path / "separate-runtime-data"), project_root=project_root,
    )

    assert _snapshot(router)["external_gate"] is False


def test_server_passes_its_computed_project_root_to_capability_router(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    from backend import mountain_capability_api, mountain_server

    received: dict[str, object] = {}

    def capture_router(registry, *, project_root):
        received["registry"] = registry
        received["project_root"] = project_root
        return mountain_capability_api.APIRouter()

    monkeypatch.setattr(mountain_capability_api, "mountain_capability_router", capture_router)
    mountain_server.create_app(tmp_path)

    assert received["project_root"] == tmp_path.resolve()
