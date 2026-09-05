"""Tests for RemotionRendererAdapter — WBS-3.

All tests mock ``subprocess.run`` so no real Node/Remotion is invoked.
Covers: command construction, output directory, failure sanitization,
timeout, non-zero exit, no side effects.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from csboard.adapters.remotion.renderer_adapter import (
    RemotionRendererAdapter,
    RemotionRenderError,
)
from csboard.domain.provider_types import RenderRequest


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_run_dir(tmp_path: Path, task_id: str = "t-001", run_id: str = "r-001") -> Path:
    """Create a minimal run directory with standard artifact layout."""
    run_dir = tmp_path / "outputs" / task_id / "runs" / run_id
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    timeline = {
        "audio_paths": ["audio/vu-1.wav"],
        "units": [
            {
                "unit_id": "vu-1",
                "duration_ms": 5000,
                "text": "hello",
                "visual_timings": [
                    {"visual_id": "img-1", "start_ms": 0, "end_ms": 5000},
                ],
            },
        ],
    }
    storyboard = {
        "infographic_storyboard": {
            "schema_version": 1,
            "engine": "infographic-remotion",
            "total_duration_ms": 5000,
            "metadata": {},
            "pages": [{
                "page_id": "page-vu-1", "title": "hello", "cue_start_ms": 0, "cue_end_ms": 5000,
                "nodes": [{"node_id": "vu-1-img-1", "kind": "image", "props": {"text": "hello", "visual_id": "img-1", "image_path": "illustrations/img-1.png"}}],
                "cues": [{"cue_id": "enter-img-1", "trigger_ms": 0, "action": "enter"}],
            }],
        },
    }
    illustration_manifest = {
        "illustrations": [
            {"visual_id": "img-1", "image_path": "illustrations/img-1.png"},
        ],
    }

    timeline_path = artifacts / "timeline.json"
    storyboard_path = artifacts / "storyboard.json"
    manifest_path = artifacts / "illustration_manifest.json"

    timeline_path.write_text(json.dumps(timeline), encoding="utf-8")
    storyboard_path.write_text(json.dumps(storyboard), encoding="utf-8")
    manifest_path.write_text(json.dumps(illustration_manifest), encoding="utf-8")

    return run_dir


def _make_request(run_dir: Path) -> RenderRequest:
    """Build a RenderRequest from a run directory."""
    artifacts = run_dir / "artifacts"
    return RenderRequest(
        timeline_path=artifacts / "timeline.json",
        storyboard_path=artifacts / "storyboard.json",
        illustration_manifest_path=artifacts / "illustration_manifest.json",
        output_dir=run_dir / "output",
        engine="infographic-remotion",
        request_id="req-001",
    )


def _make_adapter(render_mjs: Path, mock_run: Any = None) -> RemotionRendererAdapter:
    """Build an adapter with a known render.mjs path and optional mock."""
    def fake_probe(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=json.dumps({"format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "5.0"}, "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]}), stderr="")
    return RemotionRendererAdapter(
        render_mjs=render_mjs,
        node_bin="/usr/bin/node",
        timeout=300.0,
        subprocess_run=mock_run,
        ffprobe_run=fake_probe,
    )


def _ok_subprocess_result(_unused: Path = None, returncode: int = 0) -> MagicMock:
    """Build a mock subprocess.CompletedProcess for successful render.

    The mock writes a fake MP4 to the output path found in cmd[3].
    Command layout: [node, render.mjs, props.json, output.mp4, public_dir]
    """
    def side_effect(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        # Simulate render.mjs writing the output file
        # cmd[3] is output.mp4
        out = Path(cmd[3])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x00" * 1024)  # fake MP4
        return SimpleNamespace(returncode=returncode, stdout="", stderr="")

    mock = MagicMock(side_effect=side_effect)
    return mock


# ── Command construction ─────────────────────────────────────────────


class TestCommandConstruction:
    """Verify the adapter constructs the correct node render.mjs command."""

    def test_command_structure(self, tmp_path: Path) -> None:
        """Command must be: node <render.mjs> <props.json> <output.mp4> <public_dir>."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        captured_cmds: list[list[str]] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            captured_cmds.append(cmd)
            # Write fake output (cmd[3] is output.mp4)
            out = Path(cmd[3])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 512)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)
        adapter.render(request)

        assert len(captured_cmds) == 1
        cmd = captured_cmds[0]
        assert cmd[0] == "/usr/bin/node"
        assert cmd[1] == str(render_mjs)
        assert cmd[2].endswith(".json")  # props.json
        assert cmd[3].endswith(".mp4")  # output.mp4
        assert cmd[4]  # public dir is present

    def test_props_json_written_to_temp(self, tmp_path: Path) -> None:
        """The adapter must write props to a temp JSON file before calling Node."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        props_paths: list[str] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            props_path = Path(cmd[2])  # cmd[2] is props.json
            props_paths.append(str(props_path))
            assert props_path.exists(), "props.json should exist during subprocess call"
            out = Path(cmd[3])  # cmd[3] is output.mp4
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 256)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)
        adapter.render(request)

        # Temp file should be cleaned up after render
        assert len(props_paths) == 1
        assert not Path(props_paths[0]).exists(), "temp props file must be cleaned up"

    def test_props_content_valid_json(self, tmp_path: Path) -> None:
        """The props file written must contain valid JSON with required keys."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        captured_props: list[dict] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            props_path = Path(cmd[2])  # cmd[2] is props.json
            captured_props.append(json.loads(props_path.read_text(encoding="utf-8")))
            out = Path(cmd[3])  # cmd[3] is output.mp4
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 256)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)
        adapter.render(request)

        assert len(captured_props) == 1
        props = captured_props[0]
        assert props["schemaVersion"] == 1
        assert "fps" in props
        assert "width" in props
        assert "height" in props
        assert "pages" in props
        assert "totalDurationMs" in props


# ── Output directory ─────────────────────────────────────────────────


class TestOutputDirectory:
    """Verify output lands in outputs/<task>/runs/<run>/."""

    def test_output_dir_created(self, tmp_path: Path) -> None:
        """Output directory is created if it doesn't exist."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        adapter = _make_adapter(render_mjs, mock_run=_ok_subprocess_result(run_dir / "output"))
        request = _make_request(run_dir)

        # Remove output dir to test creation
        output_dir = run_dir / "output"
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)

        result = adapter.render(request)
        assert result.output_path.parent == output_dir
        assert output_dir.exists()

    def test_output_path_in_run_dir(self, tmp_path: Path) -> None:
        """Result.output_path must be inside the run directory."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        adapter = _make_adapter(render_mjs, mock_run=_ok_subprocess_result(run_dir / "output"))
        request = _make_request(run_dir)
        result = adapter.render(request)

        assert str(result.output_path).startswith(str(run_dir))


# ── Failure sanitization ─────────────────────────────────────────────


class TestFailureSanitization:
    """Error messages must not leak absolute paths, API keys, or file contents."""

    def test_stderr_sanitized_no_absolute_paths(self, tmp_path: Path) -> None:
        """Stderr with absolute paths must be sanitized in the error message."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="Error at C:\\Users\\admin\\secrets\\config.json: ENOENT",
            )

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        msg = str(exc_info.value)
        assert "C:\\Users" not in msg
        assert "secrets" not in msg

    def test_error_code_is_sanitized(self, tmp_path: Path) -> None:
        """Error code must be a known constant, not contain path fragments."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(returncode=1, stdout="", stderr="something bad")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        assert exc_info.value.code == "RENDER_FAILED"

    def test_missing_timeline_sanitized(self, tmp_path: Path) -> None:
        """Missing timeline artifact error must not include absolute path."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        adapter = _make_adapter(render_mjs, mock_run=MagicMock())
        request = _make_request(run_dir)
        # Point to non-existent file
        request = RenderRequest(
            timeline_path=run_dir / "artifacts" / "nonexistent.json",
            storyboard_path=request.storyboard_path,
            illustration_manifest_path=request.illustration_manifest_path,
            output_dir=request.output_dir,
        )

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        msg = str(exc_info.value)
        assert str(run_dir) not in msg
        assert exc_info.value.code == "ARTIFACT_NOT_FOUND"


# ── Timeout handling ─────────────────────────────────────────────────


class TestTimeoutHandling:
    """Verify subprocess.TimeoutExpired is caught and re-raised cleanly."""

    def test_timeout_raises_clean_error(self, tmp_path: Path) -> None:
        """Timeout must raise RemotionRenderError with code RENDER_TIMEOUT."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> None:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=300.0)

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        assert exc_info.value.code == "RENDER_TIMEOUT"
        assert "300" in str(exc_info.value)  # timeout value in message

    def test_timeout_cleans_up_temp_file(self, tmp_path: Path) -> None:
        """Temp props file must be cleaned up even on timeout."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        temp_files_before: list[str] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> None:
            # Record the temp file before it's cleaned up
            temp_files_before.append(cmd[1 + 1])
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=300.0)

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError):
            adapter.render(request)

        # Temp file should be cleaned up
        for f in temp_files_before:
            assert not Path(f).exists(), f"temp file {f} should be deleted after timeout"


# ── Non-zero exit ────────────────────────────────────────────────────


class TestNonZeroExit:
    """Verify non-zero exit codes raise clean errors."""

    def test_exit_code_1(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(returncode=1, stdout="", stderr="RenderError: composition not found")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        assert exc_info.value.code == "RENDER_FAILED"
        assert "exit 1" in str(exc_info.value)

    def test_exit_code_137(self, tmp_path: Path) -> None:
        """Exit 137 (SIGKILL/OOM) must raise clean error."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(returncode=137, stdout="", stderr="Killed")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        assert exc_info.value.code == "RENDER_FAILED"
        assert "exit 137" in str(exc_info.value)

    def test_nonzero_cleans_up_temp(self, tmp_path: Path) -> None:
        """Temp props file must be cleaned up on non-zero exit."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        temp_files: list[str] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            temp_files.append(cmd[1 + 1])
            return SimpleNamespace(returncode=2, stdout="", stderr="Error")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError):
            adapter.render(request)

        for f in temp_files:
            assert not Path(f).exists()


# ── No side effects ──────────────────────────────────────────────────


class TestNoSideEffects:
    """Verify the adapter doesn't produce unintended side effects."""

    def test_mock_run_not_called_on_bad_input(self, tmp_path: Path) -> None:
        """subprocess.run must NOT be called if input artifacts are missing."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        mock_run = MagicMock()
        adapter = _make_adapter(render_mjs, mock_run=mock_run)

        # Request with non-existent timeline
        request = RenderRequest(
            timeline_path=run_dir / "nonexistent.json",
            storyboard_path=run_dir / "artifacts" / "storyboard.json",
            illustration_manifest_path=run_dir / "artifacts" / "illustration_manifest.json",
            output_dir=run_dir / "output",
        )

        with pytest.raises(RemotionRenderError):
            adapter.render(request)

        mock_run.assert_not_called()

    def test_no_output_file_on_failure(self, tmp_path: Path) -> None:
        """If render fails, no orphaned output file should remain."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(returncode=1, stdout="", stderr="Error")

        adapter = _make_adapter(render_mjs, mock_run=fake_run)
        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError):
            adapter.render(request)

        output_path = request.output_dir / "infographic.mp4"
        assert not output_path.exists()

    def test_empty_storyboard_not_sent_to_node(self, tmp_path: Path) -> None:
        """Storyboard with no pages must fail before subprocess call."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        # P1-shaped empty storyboard must fail before subprocess execution.
        artifacts = run_dir / "artifacts"
        (artifacts / "storyboard.json").write_text(
            json.dumps({"infographic_storyboard": {"schema_version": 1, "engine": "infographic-remotion", "total_duration_ms": 1, "metadata": {}, "pages": []}}), encoding="utf-8",
        )
        # Overwrite timeline with empty units
        (artifacts / "timeline.json").write_text(
            json.dumps({"voice_units": [], "units": []}), encoding="utf-8",
        )

        mock_run = MagicMock()
        adapter = _make_adapter(render_mjs, mock_run=mock_run)

        request = _make_request(run_dir)

        with pytest.raises(RemotionRenderError) as exc_info:
            adapter.render(request)

        assert exc_info.value.code == "EMPTY_STORYBOARD"
        mock_run.assert_not_called()


# ── Success path ─────────────────────────────────────────────────────


class TestSuccessPath:
    """Verify a successful render returns correct RenderResult."""

    def test_result_fields(self, tmp_path: Path) -> None:
        """Successful render must populate all RenderResult fields."""
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "video_renderer" / "render.mjs"
        render_mjs.parent.mkdir(parents=True, exist_ok=True)
        render_mjs.write_text("// stub", encoding="utf-8")

        adapter = _make_adapter(render_mjs, mock_run=_ok_subprocess_result(run_dir / "output"))
        request = _make_request(run_dir)
        result = adapter.render(request)

        assert result.output_path.exists()
        assert result.duration_ms > 0
        assert result.frames > 0
        assert result.request_id == "req-001"
        assert result.provider_metadata["engine"] == "infographic-remotion"
        assert result.provider_metadata["page_count"] >= 1
        assert result.provider_metadata["render_ms"] >= 0

    def test_capabilities(self, tmp_path: Path) -> None:
        """capabilities() must return infographic-remotion engine."""
        render_mjs = tmp_path / "render.mjs"
        adapter = _make_adapter(render_mjs)
        caps = adapter.capabilities()

        assert "infographic-remotion" in caps.engines
        assert caps.max_resolution == (1920, 1080)


# ── Import guard ─────────────────────────────────────────────────────


class TestNoLegacyImports:
    """The adapter module must not import webapp or webapp.server."""

    def test_no_webapp_imports(self) -> None:
        import ast
        from pathlib import Path

        mod_path = Path(__file__).resolve().parents[1] / "csboard" / "adapters" / "remotion" / "renderer_adapter.py"
        tree = ast.parse(mod_path.read_text(encoding="utf-8"), filename=str(mod_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "webapp" not in alias.name, f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and "webapp" in node.module:
                    assert False, f"Forbidden import from: {node.module}"


class TestP2ContractGates:
    """P2-only gates: P1 props, probe verification, and declared prerequisites."""

    def test_renderer_declares_all_renderer_specific_prerequisites(self, tmp_path: Path) -> None:
        adapter = _make_adapter(tmp_path / "render.mjs")
        assert set(adapter.prerequisite_contract()) == {
            "node", "render_script", "lockfile", "remotion", "browser",
            "ffmpeg", "ffprobe", "renderer_version", "tool_versions",
        }

    def test_ffprobe_invalid_rejects_nonempty_fake_mp4(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "render.mjs"
        render_mjs.write_text("// stub", encoding="utf-8")

        def invalid_probe(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout="not-json", stderr="")

        adapter = RemotionRendererAdapter(
            render_mjs=render_mjs, node_bin="node", timeout=10,
            subprocess_run=_ok_subprocess_result(), ffprobe_run=invalid_probe,
        )
        with pytest.raises(RemotionRenderError) as error:
            adapter.render(_make_request(run_dir))
        assert error.value.code == "FFPROBE_INVALID"

    def test_props_are_v1_and_bad_json_does_not_start_node(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "render.mjs"
        render_mjs.write_text("// stub", encoding="utf-8")
        (run_dir / "artifacts" / "storyboard.json").write_text("{", encoding="utf-8")
        run = MagicMock()
        with pytest.raises(RemotionRenderError) as error:
            _make_adapter(render_mjs, mock_run=run).render(_make_request(run_dir))
        assert error.value.code == "ARTIFACT_READ_ERROR"
        run.assert_not_called()

    def test_missing_node_is_a_stable_safe_error(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "render.mjs"
        render_mjs.write_text("// stub", encoding="utf-8")

        def missing_node(*_args: Any, **_kwargs: Any) -> None:
            raise FileNotFoundError("/private/run/node")

        with pytest.raises(RemotionRenderError) as error:
            _make_adapter(render_mjs, mock_run=missing_node).render(_make_request(run_dir))
        assert error.value.code == "NODE_NOT_FOUND"
        assert "/private/run/node" not in str(error.value)

    def test_probe_dimension_mismatch_discards_candidate(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path)
        render_mjs = tmp_path / "render.mjs"
        render_mjs.write_text("// stub", encoding="utf-8")

        def wrong_dimensions(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "format": {"format_name": "mov,mp4", "duration": "5.0"},
                "streams": [{"codec_type": "video", "width": 640, "height": 360}],
            }), stderr="")

        adapter = RemotionRendererAdapter(render_mjs=render_mjs, subprocess_run=_ok_subprocess_result(), ffprobe_run=wrong_dimensions)
        request = _make_request(run_dir)
        with pytest.raises(RemotionRenderError) as error:
            adapter.render(request)
        assert error.value.code == "FFPROBE_DIMENSIONS_MISMATCH"
        assert not (request.output_dir / "infographic.mp4").exists()


# Fix typo in test — pytest will still catch it, but let's be clean
# (RemotionRenderError is already imported at top)
