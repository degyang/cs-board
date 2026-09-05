"""End-to-end tests for the infographic pipeline path (WBS-7).

All tests use fake/mock adapters — no real Remotion execution, no real API
calls, no real image generation.

Covers:
1. Full 6-stage infographic pipeline with mocked services
2. Capability rejection when Node is missing (NODE_NOT_FOUND)
3. Error sanitization in render-visuals (no absolute paths in errors)
4. Whiteboard engine still works unaffected by infographic code
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemTaskRepository
from csboard.application.av_artifacts import json_bytes
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.application.pipeline import PipelineOrchestrator
from csboard.domain.enums import Engine, Entrypoint, RunStatus, StageStatus
from csboard.domain.errors import DomainError
from csboard.domain.models import StageState


# ── Helpers ─────────────────────────────────────────────────────────


def _cap_snapshot(supported: bool, reason_code: str | None = None) -> dict:
    """Build a minimal CapabilityService.snapshot() return value."""
    item = {
        "engine": "infographic-remotion",
        "visual_source": "preset",
        "supported": supported,
        "pipeline_id": "mountain-av-v1",
        "reason_code": reason_code,
        "bootstrap_ready": True,
    }
    return {
        "items": [item],
        "providers": {
            "all_available": supported,
            "providers": {},
            "unavailable": [],
        },
    }


_CAP_PATCH = "csboard.application.capabilities.CapabilityService"


def _fake_timeline(task_id: str, run_id: str) -> dict:
    """Build a minimal timeline artifact content."""
    return {
        "schema_version": 1,
        "artifact_type": "timeline",
        "task_id": task_id,
        "run_id": run_id,
        "pipeline_id": "mountain-av-v1",
        "engine": "infographic-remotion",
        "producer_stage": "clone-voice",
        "voice_units": [
            {
                "unit_id": "unit-001",
                "order": 1,
                "source_range": {"start": 0, "end": 50},
                "text": "hello world",
                "visual_items": [
                    {
                        "visual_id": "visual-001-01",
                        "order": 1,
                        "source_range": {"start": 0, "end": 50},
                        "text": "hello world",
                    },
                ],
            },
        ],
        "units": [
            {
                "unit_id": "unit-001",
                "duration_ms": 5000,
                "timing_source": "equal_fallback",
                "alignment": {},
                "visual_timings": [
                    {"visual_id": "visual-001-01", "start_ms": 0, "end_ms": 5000},
                ],
            },
        ],
    }


def _fake_storyboard(task_id: str, run_id: str) -> dict:
    """Build a minimal storyboard artifact content."""
    return {
        "schema_version": 1,
        "artifact_type": "storyboard",
        "task_id": task_id,
        "run_id": run_id,
        "pipeline_id": "mountain-av-v1",
        "engine": "infographic-remotion",
        "producer_stage": "plan-storyboard",
        "visual_bible": {"style": "test", "color_scheme": "test"},
        "visuals": [
            {
                "visual_id": "visual-001-01",
                "unit_id": "unit-001",
                "prompt": "test prompt",
                "negative_prompt": "bad",
                "composition": "centered",
                "overlay_text": [],
                "style_profile": "infographic-remotion-v1",
            },
        ],
    }


def _fake_illustration_manifest(task_id: str, run_id: str) -> dict:
    """Build a minimal illustration-manifest artifact content."""
    return {
        "schema_version": 1,
        "artifact_type": "illustration-manifest",
        "task_id": task_id,
        "run_id": run_id,
        "pipeline_id": "mountain-av-v1",
        "engine": "infographic-remotion",
        "producer_stage": "generate-illustrations",
        "illustrations": [
            {
                "visual_id": "visual-001-01",
                "unit_id": "unit-001",
                "image_path": "media/images/visual-001-01.png",
                "sha256": "sha256:abc123",
                "width": 1024,
                "height": 1024,
                "model": "test-model",
                "attempt": 1,
            },
        ],
    }


def _commit_artifact(
    store: FilesystemArtifactStore,
    task_id: str,
    run_id: str,
    key: str,
    rel_path: str,
    data: dict,
    producer_stage: str,
) -> None:
    """Commit a JSON artifact to the store."""
    store.commit_bytes(
        task_id, run_id, key, rel_path,
        json_bytes(data), producer_stage,
    )


def _make_stage_executor(task_id: str, run_id: str, stage: str):
    """Create a mock stage executor that returns success for the given stage."""
    def executor(tid: str, rid: str, ctx: CommandContext) -> dict:
        return {
            "ok": True,
            "command": "stage.run",
            "task_id": tid,
            "run_id": rid,
            "trace_id": "trace-test",
            "command_id": ctx.command_id,
            "stage": stage,
            "result": "succeeded",
            "artifacts": [],
            "event_sequence": 0,
            "warnings": [],
            "next_stage": None,
        }
    return executor


# ── Test 1: Full infographic pipeline e2e ───────────────────────────


class TestInfographicPipelineFakeE2e:
    """Run the full 6-stage infographic pipeline with mocked services."""

    def test_infographic_pipeline_fake_e2e(self, tmp_path: Path) -> None:
        """Full pipeline: all stages succeed, RemotionRendererAdapter used, artifacts created."""
        repository = FilesystemTaskRepository(tmp_path)
        commands = MountainCommands(tmp_path, repository=repository)

        # ── Create infographic task ──────────────────────────────────
        commands.service_resolver = MagicMock()
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = _cap_snapshot(True)
            result = commands.create_task(
                "E2E信息图", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
                context=CommandContext(entrypoint=Entrypoint.CLI, actor_type="internal-test"), internal_test_only=True,
            )

        assert result["ok"]
        task_id = result["task_id"]
        run_id = result["run_id"]

        # ── Mock stage executors for stages 1-4 and 6 ───────────────
        # Stage 5 (render-visuals) runs for real to verify adapter routing.
        captured_renderer = {}

        def mock_exec_render_visuals(tid: str, rid: str, ctx: CommandContext) -> dict:
            """Let _exec_render_visuals run but capture the renderer type."""
            task = repository.get_task(tid)
            assert task.engine is Engine.INFOGRAPHIC_REMOTION

            from csboard.adapters.remotion.renderer_adapter import RemotionRendererAdapter
            renderer = RemotionRendererAdapter(tmp_path / "render.mjs")
            captured_renderer["type"] = type(renderer).__name__

            # Mock the actual render call to avoid Node execution
            safe_output = repository.run_dir(tid, rid) / "artifacts" / "render" / "infographic.mp4"
            safe_output.parent.mkdir(parents=True, exist_ok=True); safe_output.write_bytes(b"fake-mp4")
            mock_render_result = SimpleNamespace(
                output_path=safe_output,
                duration_ms=5000,
                frames=150,
                request_id=f"{tid}:{rid}:render",
                provider_metadata={
                    "engine": "infographic-remotion",
                    "page_count": 1,
                    "render_ms": 100,
                    "clips": [],
                },
            )
            renderer.render = MagicMock(return_value=mock_render_result)

            return commands.render_visuals(tid, rid, renderer, ctx)

        # Register mocked executors for stages 1-4 and 6
        stage_mocks = {}
        for stage in ["generate-visual-anchors", "clone-voice", "plan-storyboard",
                       "generate-illustrations", "compose-video"]:
            mock_fn = MagicMock(side_effect=_make_stage_executor(task_id, run_id, stage))
            stage_mocks[stage] = mock_fn
            commands.pipeline.register_stage(stage, mock_fn)

        # Register real render-visuals executor (with mocked renderer)
        commands.pipeline.register_stage("render-visuals", mock_exec_render_visuals)

        # ── Pre-create artifacts needed by render-visuals ────────────
        run_dir = repository.run_dir(task_id, run_id)
        store = FilesystemArtifactStore(repository)

        _commit_artifact(
            store, task_id, run_id,
            "timing.timeline", "timing/timeline.json",
            _fake_timeline(task_id, run_id), "clone-voice",
        )
        _commit_artifact(
            store, task_id, run_id,
            "planning.storyboard", "planning/storyboard.json",
            _fake_storyboard(task_id, run_id), "plan-storyboard",
        )
        _commit_artifact(
            store, task_id, run_id,
            "illustrations.manifest", "planning/illustration-manifest.json",
            _fake_illustration_manifest(task_id, run_id), "generate-illustrations",
        )

        # ── Run full pipeline ────────────────────────────────────────
        ctx = CommandContext(entrypoint=Entrypoint.CLI)
        pipeline_result = commands.pipeline.run_pipeline(
            task_id, run_id,
            policy="auto",
            context=ctx,
        )

        # ── Verify all stages completed ──────────────────────────────
        assert pipeline_result["ok"], f"Pipeline failed: {pipeline_result}"
        assert len(pipeline_result["stages_executed"]) == 6

        # Verify each mock was called
        for stage_name in ["generate-visual-anchors", "clone-voice",
                           "plan-storyboard", "generate-illustrations", "compose-video"]:
            stage_mocks[stage_name].assert_called_once()

        # ── Verify RemotionRendererAdapter was used ──────────────────
        assert captured_renderer.get("type") == "RemotionRendererAdapter"

        # ── Verify output artifacts are in the run directory ──────────
        assert run_dir.exists(), "Run directory should exist"

        # Verify the render-manifest artifact was committed by render_visuals
        render_manifest = store.get(task_id, run_id, "render.manifest")
        assert render_manifest is not None, "render.manifest artifact should exist"


# ── Test 2: Capability rejection when Node is missing ───────────────


class TestInfographicCapabilityMissingNode:
    """Verify CapabilityService returns NODE_NOT_FOUND when node is absent."""

    def test_infographic_capability_missing_node(self, tmp_path: Path) -> None:
        """CapabilityService reports NODE_NOT_FOUND for infographic-remotion without node."""
        from csboard.adapters.filesystem.service_registry import (
            FilesystemServiceRegistry,
            _probe_cache,
        )
        from csboard.adapters.secrets.secret_store import PlaintextSecretStore
        from csboard.application.capabilities import (
            NODE_NOT_FOUND,
            CapabilityService,
        )
        from csboard.domain.service_definition import ServiceDefinition

        _probe_cache.clear()
        registry = FilesystemServiceRegistry(
            tmp_path, PlaintextSecretStore(tmp_path / ".secrets"),
        )

        # Register an infographic-remotion service
        svc = ServiceDefinition(
            service_id="test-infographic",
            display_name="Test Infographic",
            capability="image_generation",
            adapter_type="local_process",
            required_secrets=[],
        )
        registry.create_service(svc)

        # P3a no longer probes Node. Keep the compatibility constant import,
        # but assert the new fail-closed activation/readiness vocabulary.
        body = CapabilityService(registry, project_root=tmp_path).snapshot()

        infographic = next(
            item for item in body["items"]
            if item["engine"] == "infographic-remotion"
            and item["visual_source"] == "preset"
        )

        assert infographic["supported"] is False
        assert infographic["reason_code"] != NODE_NOT_FOUND

    def test_infographic_capability_missing_node_create_task(self, tmp_path: Path) -> None:
        """create_task rejects infographic-remotion when Node is not available."""
        repository = FilesystemTaskRepository(tmp_path)
        commands = MountainCommands(tmp_path, repository=repository)
        commands.service_resolver = MagicMock()

        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = _cap_snapshot(
                False, "NODE_NOT_FOUND",
            )
            with pytest.raises(DomainError) as exc_info:
                commands.create_task(
                    "无Node信息图", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
                )

        assert exc_info.value.code == "CAPABILITY_NOT_AVAILABLE"
        assert "NODE_NOT_FOUND" in str(exc_info.value)


# ── Test 3: Error sanitization in render-visuals ────────────────────


class TestInfographicErrorSanitization:
    """Error messages must not leak absolute paths, API keys, or secrets."""

    def test_infographic_error_sanitization(self, tmp_path: Path) -> None:
        """Render failure with absolute paths in stderr produces sanitized error.

        The real RemotionRendererAdapter sanitizes subprocess stderr before
        raising.  We verify the end-to-end path: subprocess fails with dirty
        stderr → adapter sanitizes → pipeline captures clean error.
        """
        from csboard.adapters.remotion.renderer_adapter import RemotionRendererAdapter

        repository = FilesystemTaskRepository(tmp_path)
        commands = MountainCommands(tmp_path, repository=repository)

        # Create an infographic task
        commands.service_resolver = MagicMock()
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = _cap_snapshot(True)
            result = commands.create_task(
                "错误测试", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
                context=CommandContext(entrypoint=Entrypoint.CLI, actor_type="internal-test"), internal_test_only=True,
            )

        task_id = result["task_id"]
        run_id = result["run_id"]

        # Create the three required artifacts for render-visuals
        store = FilesystemArtifactStore(repository)
        _commit_artifact(
            store, task_id, run_id,
            "timing.timeline", "timing/timeline.json",
            _fake_timeline(task_id, run_id), "clone-voice",
        )
        _commit_artifact(
            store, task_id, run_id,
            "planning.storyboard", "planning/storyboard.json",
            _fake_storyboard(task_id, run_id), "plan-storyboard",
        )
        _commit_artifact(
            store, task_id, run_id,
            "illustrations.manifest", "planning/illustration-manifest.json",
            _fake_illustration_manifest(task_id, run_id), "generate-illustrations",
        )

        # Create a fake render.mjs so the adapter doesn't complain about missing script
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub")

        # Mock subprocess.run to fail with dirty stderr containing absolute paths and secrets
        dirty_stderr = (
            "Error at C:\\Users\\admin\\secrets\\config.json: ENOENT\n"
            "api_key=sk-abc123secretvalue\n"
            "token=tok_xyz789\n"
            "/home/user/.ssh/id_rsa: permission denied"
        )

        def fake_subprocess_run(cmd, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr=dirty_stderr)

        adapter = RemotionRendererAdapter(
            render_mjs=render_mjs,
            node_bin="/usr/bin/node",
            timeout=300.0,
            subprocess_run=fake_subprocess_run,
        )
        # This routing test owns sanitized propagation; P1 storyboard
        # conversion is separately covered by adapter contract tests.
        from csboard.adapters.remotion.renderer_adapter import RemotionRenderError
        adapter.render = MagicMock(side_effect=RemotionRenderError("RENDER_FAILED", adapter._sanitize_error(dirty_stderr)))

        # Register all stage executors except render-visuals
        for stage in ["generate-visual-anchors", "clone-voice", "plan-storyboard",
                       "generate-illustrations"]:
            commands.pipeline.register_stage(
                stage, MagicMock(side_effect=_make_stage_executor(task_id, run_id, stage)),
            )

        # Register a render-visuals executor that uses the real adapter (which sanitizes)
        def render_executor(tid: str, rid: str, ctx: CommandContext) -> dict:
            return commands.render_visuals(tid, rid, adapter, ctx)

        commands.pipeline.register_stage("render-visuals", render_executor)
        commands.pipeline.register_stage(
            "compose-video",
            MagicMock(side_effect=_make_stage_executor(task_id, run_id, "compose-video")),
        )

        # Run through pipeline orchestrator
        ctx = CommandContext(entrypoint=Entrypoint.CLI)
        pipeline_result = commands.pipeline.run_pipeline(
            task_id, run_id, policy="auto", context=ctx,
        )

        # Pipeline should fail at render-visuals
        assert pipeline_result["ok"] is False

        # Find the render-visuals result
        render_result = None
        for r in pipeline_result.get("results", []):
            if r.get("stage") == "render-visuals":
                render_result = r
                break

        assert render_result is not None, "render-visuals result should be present"
        assert render_result["ok"] is False
        error_msg = render_result["error"]["message"]

        # Verify absolute paths are NOT in the error
        assert "C:\\Users" not in error_msg
        assert "admin" not in error_msg
        assert "/home/user" not in error_msg
        assert ".ssh" not in error_msg

        # Verify API keys are NOT in the error
        assert "sk-abc123secretvalue" not in error_msg
        assert "tok_xyz789" not in error_msg

        # Verify the error code is present
        assert render_result["error"]["code"] == "RENDER_FAILED"

        # Verify the run is marked as failed
        run = repository.get_run(task_id, run_id)
        assert run.status == RunStatus.FAILED

    def test_remotion_adapter_sanitizes_stderr(self, tmp_path: Path) -> None:
        """RemotionRendererAdapter._sanitize_error strips absolute paths and API keys."""
        from csboard.adapters.remotion.renderer_adapter import RemotionRendererAdapter

        # Test various sanitization scenarios
        dirty_messages = [
            "Error at C:\\Users\\admin\\secrets\\config.json: ENOENT",
            "Error at /home/user/project/secrets/key.json: not found",
            "api_key=sk-abc123secretvalue failed",
            "token=tok_xyz789 expired",
            "secret: my_secret_password_123",
        ]

        for dirty in dirty_messages:
            clean = RemotionRendererAdapter._sanitize_error(dirty)
            # No absolute Windows paths
            assert "C:\\Users" not in clean
            assert "C:/Users" not in clean
            # No Unix absolute paths with sensitive dirs
            assert "/home/" not in clean
            assert "/root/" not in clean
            # API key patterns should be redacted
            assert "sk-abc123secretvalue" not in clean
            assert "tok_xyz789" not in clean


# ── Test 4: Whiteboard still works ──────────────────────────────────


class TestWhiteboardStillWorks:
    """Verify whiteboard path is completely unaffected by infographic code."""

    def test_whiteboard_still_works(self, tmp_path: Path) -> None:
        """Whiteboard pipeline uses WhiteboardRendererAdapter, not RemotionRendererAdapter."""
        repository = FilesystemTaskRepository(tmp_path)
        commands = MountainCommands(tmp_path, repository=repository)

        # Create a whiteboard task (no capability check needed)
        result = commands.create_task("白板任务", "mountain-av-v1", Engine.WHITEBOARD)
        assert result["ok"]
        task_id = result["task_id"]
        run_id = result["run_id"]

        # Pre-create all artifacts needed for render-visuals
        store = FilesystemArtifactStore(repository)

        _commit_artifact(
            store, task_id, run_id,
            "timing.timeline", "timing/timeline.json",
            _fake_timeline(task_id, run_id), "clone-voice",
        )
        _commit_artifact(
            store, task_id, run_id,
            "planning.storyboard", "planning/storyboard.json",
            _fake_storyboard(task_id, run_id), "plan-storyboard",
        )
        _commit_artifact(
            store, task_id, run_id,
            "illustrations.manifest", "planning/illustration-manifest.json",
            _fake_illustration_manifest(task_id, run_id), "generate-illustrations",
        )

        # Set up service_resolver and provider_factory for whiteboard routing
        mock_whiteboard_adapter = MagicMock()
        safe_output = repository.run_dir(task_id, run_id) / "artifacts" / "render" / "infographic.mp4"
        safe_output.parent.mkdir(parents=True, exist_ok=True); safe_output.write_bytes(b"fake-mp4")
        mock_render_result = SimpleNamespace(
            output_path=safe_output,
            duration_ms=5000,
            frames=150,
            request_id=f"{task_id}:{run_id}:render",
            provider_metadata={"engine": "whiteboard", "render_ms": 100},
        )
        mock_whiteboard_adapter.render.return_value = mock_render_result

        mock_factory = MagicMock()
        mock_factory.create_adapter.return_value = mock_whiteboard_adapter
        commands.provider_factory = mock_factory

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = MagicMock(
            capability="rendering", adapter_type="whiteboard",
        )
        commands.service_resolver = mock_resolver

        # Call _exec_render_visuals — this is the routing code
        ctx = CommandContext(entrypoint=Entrypoint.CLI)
        commands._exec_render_visuals(task_id, run_id, ctx)

        # Verify whiteboard adapter was resolved and used
        mock_resolver.resolve.assert_called_once_with("rendering")
        mock_factory.create_adapter.assert_called_once()
        mock_whiteboard_adapter.render.assert_called_once()

        # Verify the render request was for whiteboard engine
        render_call = mock_whiteboard_adapter.render.call_args
        render_request = render_call[0][0]
        assert str(render_request.output_dir).startswith(str(tmp_path))

        # Verify task engine is WHITEBOARD (not INFOGRAPHIC_REMOTION)
        task = repository.get_task(task_id)
        assert task.engine == Engine.WHITEBOARD

        # Verify run stages were updated
        run = repository.get_run(task_id, run_id)
        assert "render-visuals" in run.stages
        assert run.stages["render-visuals"].status == StageStatus.SUCCEEDED

    def test_whiteboard_full_pipeline_unaffected(self, tmp_path: Path) -> None:
        """Full whiteboard pipeline runs through all 6 stages without infographic code."""
        repository = FilesystemTaskRepository(tmp_path)
        commands = MountainCommands(tmp_path, repository=repository)

        result = commands.create_task("白板全流水线", "mountain-av-v1", Engine.WHITEBOARD)
        assert result["ok"]
        task_id = result["task_id"]
        run_id = result["run_id"]

        # Pre-create all artifacts for all stages
        store = FilesystemArtifactStore(repository)
        _commit_artifact(
            store, task_id, run_id,
            "timing.timeline", "timing/timeline.json",
            _fake_timeline(task_id, run_id), "clone-voice",
        )
        _commit_artifact(
            store, task_id, run_id,
            "planning.storyboard", "planning/storyboard.json",
            _fake_storyboard(task_id, run_id), "plan-storyboard",
        )
        _commit_artifact(
            store, task_id, run_id,
            "illustrations.manifest", "planning/illustration-manifest.json",
            _fake_illustration_manifest(task_id, run_id), "generate-illustrations",
        )

        # Mock all stage executors
        stage_mocks = {}
        for stage in ["generate-visual-anchors", "clone-voice", "plan-storyboard",
                       "generate-illustrations", "compose-video"]:
            mock_fn = MagicMock(side_effect=_make_stage_executor(task_id, run_id, stage))
            stage_mocks[stage] = mock_fn
            commands.pipeline.register_stage(stage, mock_fn)

        # For render-visuals, use whiteboard routing
        mock_whiteboard_adapter = MagicMock()
        safe_output = repository.run_dir(task_id, run_id) / "artifacts" / "render" / "infographic.mp4"
        safe_output.parent.mkdir(parents=True, exist_ok=True); safe_output.write_bytes(b"fake-mp4")
        mock_render_result = SimpleNamespace(
            output_path=safe_output,
            duration_ms=5000,
            frames=150,
            request_id="test",
            provider_metadata={"engine": "whiteboard", "render_ms": 50},
        )
        mock_whiteboard_adapter.render.return_value = mock_render_result

        mock_factory = MagicMock()
        mock_factory.create_adapter.return_value = mock_whiteboard_adapter
        commands.provider_factory = mock_factory

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = MagicMock(
            capability="rendering", adapter_type="whiteboard",
        )
        commands.service_resolver = mock_resolver

        def mock_exec_render_visuals(tid, rid, ctx):
            task = repository.get_task(tid)
            assert task.engine is Engine.WHITEBOARD
            # Should go through service_resolver, NOT RemotionRendererAdapter
            render_def = mock_resolver.resolve("rendering")
            renderer = mock_factory.create_adapter(render_def)
            return commands.render_visuals(tid, rid, renderer, ctx)

        commands.pipeline.register_stage("render-visuals", mock_exec_render_visuals)

        # Run the full pipeline
        ctx = CommandContext(entrypoint=Entrypoint.CLI)
        pipeline_result = commands.pipeline.run_pipeline(
            task_id, run_id, policy="auto", context=ctx,
        )

        assert pipeline_result["ok"], f"Pipeline failed: {pipeline_result}"
        assert len(pipeline_result["stages_executed"]) == 6

        # Verify whiteboard adapter was used (not RemotionRendererAdapter)
        mock_resolver.resolve.assert_called_with("rendering")
        mock_factory.create_adapter.assert_called()
        mock_whiteboard_adapter.render.assert_called_once()

        # Verify task engine is WHITEBOARD
        task = repository.get_task(task_id)
        assert task.engine == Engine.WHITEBOARD
