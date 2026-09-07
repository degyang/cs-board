"""The create surface and task command consume one activation projection."""
from __future__ import annotations

import json
from pathlib import Path
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry, _probe_cache
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.activation import ActivationVerifier
from csboard.application.capabilities import CapabilityService
from csboard.application.commands import MountainCommands
from csboard.domain.enums import Engine
from csboard.domain.errors import DomainError
from csboard.domain.service_definition import ServiceDefinition
from tests.infographic_activation_fixture import RUN, TASK, create_root, sha, write_pointer


TOOLCHAIN = (
    "node", "render-script", "lockfile", "locked-remotion", "remotion-browser", "ffmpeg", "ffprobe",
)


def _snapshot(supported: bool) -> dict:
    return {"items": [{"engine": "infographic-remotion", "visual_source": "preset",
                       "pipeline_id": "mountain-av-v1", "supported": supported,
                       "reason_code": None if supported else "EVIDENCE_MISSING"}],
            "providers": {"all_available": supported, "providers": {}, "unavailable": []}}


def test_create_options_and_new_task_share_the_activated_projection(tmp_path: Path):
    commands = MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path))
    commands.service_resolver = MagicMock()
    with patch("csboard.application.capabilities.CapabilityService") as capability:
        capability.return_value.snapshot.return_value = _snapshot(True)
        option = next(item for item in commands.create_options()["engines"] if item["id"] == "infographic-remotion")
        created = commands.create_task("activated", engine=Engine.INFOGRAPHIC_REMOTION)
    assert option["available"] is True
    assert created["ok"] is True


def test_closed_projection_rejects_task_with_stable_code(tmp_path: Path):
    commands = MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path))
    commands.service_resolver = MagicMock()
    with patch("csboard.application.capabilities.CapabilityService") as capability:
        capability.return_value.snapshot.return_value = _snapshot(False)
        try:
            commands.create_task("closed", engine=Engine.INFOGRAPHIC_REMOTION)
        except Exception as error:
            assert getattr(error, "code", None) == "CAPABILITY_NOT_AVAILABLE"
        else:
            raise AssertionError("closed activation must reject task creation")


def _runner(command, **_kwargs):
    if command[0] == "ffprobe" and "-show_streams" in command:
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080}],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "2.0"},
        }))
    return SimpleNamespace(returncode=0, stdout={
        "node": "v-test", "ffmpeg": "ffmpeg fixture", "ffprobe": "ffprobe fixture",
    }[command[0]] + "\n")


def _ready_toolchain(_root: object) -> list[dict[str, object]]:
    return [{"component": component, "ready": True, "reason_code": None} for component in TOOLCHAIN]


def _registry(root: Path) -> FilesystemServiceRegistry:
    _probe_cache.clear()
    registry = FilesystemServiceRegistry(root, PlaintextSecretStore(root / ".secrets"))
    for suffix, capability in (
        ("text", "text_generation"), ("voice", "speech_synthesis"),
        ("align", "speech_alignment"), ("image", "image_generation"), ("media", "media"),
    ):
        service_id = f"fixture-{suffix}"
        registry.create_service(ServiceDefinition(
            service_id=service_id, display_name=service_id, capability=capability,
            adapter_type="local_process", required_secrets=[],
        ))
        _probe_cache[service_id] = ({"available": True, "error_code": None}, time.monotonic())
    return registry


def _activation_factory(root: Path, fingerprint: str) -> ActivationVerifier:
    return ActivationVerifier(
        root,
        current_service_fingerprint=fingerprint,
        runner=_runner,
        browser_version=lambda: "Chrome fixture",
    )


def _write_live_fixture(root: Path, registry: FilesystemServiceRegistry) -> None:
    create_root(root)
    service = CapabilityService(
        registry, project_root=root, external_stage_gate=lambda: True,
        toolchain_probe=_ready_toolchain, activation_verifier_factory=_activation_factory,
    )
    bootstrap = service._bootstrap_snapshot(service._unique_services())
    fingerprint = service._service_fingerprint(service._unique_services(), bootstrap["bootstrap_diagnostics"])
    write_pointer(root, service_fingerprint=fingerprint)


def test_live_capability_projection_drives_options_and_creation_then_fails_closed(tmp_path: Path):
    """No CapabilityService mock: all three consumers re-read one V3 fixture."""
    registry = _registry(tmp_path)
    _write_live_fixture(tmp_path, registry)
    commands = MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path))
    commands.service_resolver = SimpleNamespace(_registry=registry)

    def capability_factory(actual_registry, **kwargs):
        return CapabilityService(
            actual_registry, toolchain_probe=_ready_toolchain,
            activation_verifier_factory=_activation_factory, **kwargs,
        )

    commands.capability_service_factory = capability_factory
    snapshot = commands._capability_service().snapshot()
    item = next(value for value in snapshot["items"] if value["engine"] == "infographic-remotion")
    option = next(value for value in commands.create_options()["engines"] if value["id"] == "infographic-remotion")
    assert item["supported"] is True and option["available"] is True
    assert commands.create_task("live activated", engine=Engine.INFOGRAPHIC_REMOTION)["ok"] is True

    mp4 = tmp_path / "outputs" / TASK / "runs" / RUN / "artifacts/render/infographic.mp4"
    mp4.write_bytes(b"invalidated")
    snapshot = commands._capability_service().snapshot()
    item = next(value for value in snapshot["items"] if value["engine"] == "infographic-remotion")
    option = next(value for value in commands.create_options()["engines"] if value["id"] == "infographic-remotion")
    assert item["supported"] is False and option["available"] is False
    with pytest.raises(DomainError) as error:
        commands.create_task("live closed", engine=Engine.INFOGRAPHIC_REMOTION)
    assert error.value.code == "CAPABILITY_NOT_AVAILABLE"
