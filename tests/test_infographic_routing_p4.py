"""P4-only controlled routing tests; all renderers are fake."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemTaskRepository
from csboard.application.av_artifacts import json_bytes
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.domain.enums import Engine, Entrypoint, RunStatus, StageStatus
from csboard.domain.errors import DomainError


def _bootstrap() -> dict:
    return {"items": [{"engine": "infographic-remotion", "visual_source": "preset", "supported": False,
                        "bootstrap_ready": True, "reason_code": "REAL_SMOKE_EVIDENCE_REQUIRED"}], "providers": {}}


def _context() -> CommandContext:
    return CommandContext(entrypoint=Entrypoint.CLI, actor_type="internal-test")


def _create(tmp_path: Path) -> tuple[MountainCommands, str, str]:
    repository = FilesystemTaskRepository(tmp_path)
    commands = MountainCommands(tmp_path, repository=repository)
    commands.service_resolver = MagicMock()
    with patch("csboard.application.capabilities.CapabilityService") as capability:
        capability.return_value.snapshot.return_value = _bootstrap()
        result = commands.create_task("P4 fake", engine=Engine.INFOGRAPHIC_REMOTION,
                                      context=_context(), internal_test_only=True)
    return commands, result["task_id"], result["run_id"]


def _inputs(commands: MountainCommands, task_id: str, run_id: str) -> None:
    store = FilesystemArtifactStore(commands.repository)
    for key, name in (("timing.timeline", "timeline"), ("planning.storyboard", "storyboard"), ("illustrations.manifest", "illustrations")):
        store.commit_bytes(task_id, run_id, key, f"p4/{name}.json", json_bytes({"task_id": task_id, "run_id": run_id}), "test")


def test_public_create_is_rejected_but_controlled_internal_accepts(tmp_path: Path) -> None:
    repository = FilesystemTaskRepository(tmp_path)
    commands = MountainCommands(tmp_path, repository=repository); commands.service_resolver = MagicMock()
    with patch("csboard.application.capabilities.CapabilityService") as capability:
        capability.return_value.snapshot.return_value = _bootstrap()
        with pytest.raises(DomainError) as rejected:
            commands.create_task("public", engine=Engine.INFOGRAPHIC_REMOTION)
        assert rejected.value.code == "CAPABILITY_NOT_AVAILABLE"
        accepted = commands.create_task("internal", engine=Engine.INFOGRAPHIC_REMOTION,
                                        context=_context(), internal_test_only=True)
    assert repository.get_task(accepted["task_id"]).engine is Engine.INFOGRAPHIC_REMOTION


def test_remotion_only_render_is_indexed_and_failed_run_is_retryable(tmp_path: Path) -> None:
    commands, task_id, run_id = _create(tmp_path); _inputs(commands, task_id, run_id)
    selected: list[str] = []
    class FakeRemotion:
        def render(self, request):
            selected.append(type(self).__name__)
            output = request.output_dir / "infographic.mp4"; output.write_bytes(b"fake-mp4")
            return SimpleNamespace(output_path=output, duration_ms=1000, frames=30,
                                   provider_metadata={"engine": "infographic-remotion", "clips": [], "probe": {"duration": 1}})
    commands.infographic_renderer_factory = FakeRemotion
    commands.provider_factory = MagicMock(); commands.service_resolver.resolve.side_effect = AssertionError("generic rendering forbidden")
    result = commands._exec_render_visuals(task_id, run_id, _context())
    index = json.loads((commands.repository.run_dir(task_id, run_id) / "artifacts" / "index.json").read_text())
    manifest = FilesystemArtifactStore(commands.repository).get(task_id, run_id, "render.manifest")
    assert selected == ["FakeRemotion"] and {"render.video", "render.manifest"} <= set(index["artifacts"])
    assert manifest and manifest["relative_path"] == "render/render-manifest.json"
    assert result["artifacts"] == ["render.video", "render.manifest"]

    class FailingRemotion:
        def render(self, request): raise RuntimeError("fake failure")
    commands.infographic_renderer_factory = FailingRemotion
    with pytest.raises(RuntimeError): commands._exec_render_visuals(task_id, run_id, _context())
    run = commands.repository.get_run(task_id, run_id)
    assert run.status is RunStatus.FAILED and run.stages["render-visuals"].status is StageStatus.FAILED


def test_cross_run_or_escaped_input_is_rejected(tmp_path: Path) -> None:
    commands, task_id, run_id = _create(tmp_path); _inputs(commands, task_id, run_id)
    store = FilesystemArtifactStore(commands.repository)
    store.commit_bytes(task_id, run_id, "timing.timeline", "p4/timeline.json", json_bytes({"task_id": task_id, "run_id": "run-other"}), "test")
    commands.infographic_renderer_factory = MagicMock()
    with pytest.raises(DomainError) as rejected:
        commands._exec_render_visuals(task_id, run_id, _context())
    assert rejected.value.code == "ARTIFACT_RUN_MISMATCH"


def test_fake_six_stage_e2e_keeps_one_run_trace_and_artifact_tree(tmp_path: Path) -> None:
    commands, task_id, run_id = _create(tmp_path); _inputs(commands, task_id, run_id)
    class FakeRemotion:
        def render(self, request):
            output = request.output_dir / "infographic.mp4"; output.write_bytes(b"fake-mp4")
            return SimpleNamespace(output_path=output, duration_ms=1000, frames=30,
                                   provider_metadata={"clips": [], "probe": {"duration": 1}})
    commands.infographic_renderer_factory = FakeRemotion
    def fake(stage):
        def execute(tid, rid, context):
            run = commands.repository.get_run(tid, rid)
            run.stages[stage] = __import__("csboard.domain.models", fromlist=["StageState"]).StageState(StageStatus.SUCCEEDED, 1)
            commands.repository.save_run(run)
            return {"ok": True, "stage": stage, "result": "succeeded", "task_id": tid, "run_id": rid}
        return execute
    for stage in ("generate-visual-anchors", "clone-voice", "plan-storyboard", "generate-illustrations", "compose-video"):
        commands.pipeline.register_stage(stage, fake(stage))
    outcome = commands.pipeline.run_pipeline(task_id, run_id, context=_context())
    run = commands.repository.get_run(task_id, run_id)
    assert outcome["ok"] and outcome["stages_executed"] == ["generate-visual-anchors", "clone-voice", "plan-storyboard", "generate-illustrations", "render-visuals", "compose-video"]
    assert run.status is RunStatus.SUCCEEDED and all(state.status is StageStatus.SUCCEEDED for state in run.stages.values())
    assert (commands.repository.run_dir(task_id, run_id) / "artifacts" / "render" / "render-manifest.json").is_file()
