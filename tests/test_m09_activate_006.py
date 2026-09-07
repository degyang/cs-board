"""Create-options reason projection regression coverage for M09 activation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.application.commands import MountainCommands


def _commands(tmp_path: Path, *, supported: bool, reason_code: object) -> MountainCommands:
    commands = MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path))
    commands.service_resolver = SimpleNamespace(_registry=object())
    snapshot = {
        "items": [{
            "engine": "infographic-remotion",
            "visual_source": "preset",
            "supported": supported,
            "reason_code": reason_code,
        }],
    }
    commands.capability_service_factory = lambda _registry, **_kwargs: SimpleNamespace(
        snapshot=lambda: snapshot,
    )
    return commands


def _infographic_option(commands: MountainCommands) -> dict:
    return next(item for item in commands.create_options()["engines"] if item["id"] == "infographic-remotion")


def test_available_infographic_has_no_unavailable_reason(tmp_path: Path):
    option = _infographic_option(_commands(tmp_path, supported=True, reason_code=None))

    assert option == {
        "id": "infographic-remotion",
        "label": "动态信息图",
        "available": True,
    }


def test_unavailable_infographic_preserves_reason_code(tmp_path: Path):
    option = _infographic_option(_commands(tmp_path, supported=False, reason_code="EVIDENCE_MISSING"))

    assert option["available"] is False
    assert option["reason"] == "EVIDENCE_MISSING"


@pytest.mark.parametrize("reason_code", [None, "", 17])
def test_unavailable_infographic_without_valid_reason_fails_closed(tmp_path: Path, reason_code: object):
    option = _infographic_option(_commands(tmp_path, supported=False, reason_code=reason_code))

    assert option["available"] is False
    assert option["reason"] == "CAPABILITY_NOT_AVAILABLE"
