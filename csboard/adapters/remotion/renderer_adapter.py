"""P2 RendererPort adapter for P1 infographic contracts; no legacy imports."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from csboard.adapters.remotion.storyboard_adapter import InfographicStoryboardAdapter, StoryboardConversionError
from csboard.domain.infographic import InfographicContractError, InfographicStoryboard, duration_frames
from csboard.domain.provider_types import RenderRequest, RenderResult, RendererCapabilities

# Contract declaration only. P3a/P4 own probing and readiness decisions.
RENDERER_PREREQUISITES = ("node", "render_script", "lockfile", "remotion", "browser", "ffmpeg", "ffprobe", "renderer_version", "tool_versions")


class RemotionRenderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class RemotionRendererAdapter:
    def __init__(self, render_mjs: Path | str, node_bin: str = "node", ffprobe_bin: str = "ffprobe", timeout: float = 600.0, subprocess_run: Callable[..., Any] | None = None, ffprobe_run: Callable[..., Any] | None = None) -> None:
        self._render_mjs, self._node, self._ffprobe, self._timeout = Path(render_mjs), node_bin, ffprobe_bin, timeout
        self._run, self._probe = subprocess_run or subprocess.run, ffprobe_run or subprocess.run

    @staticmethod
    def prerequisite_contract() -> tuple[str, ...]: return RENDERER_PREREQUISITES
    def capabilities(self) -> RendererCapabilities: return RendererCapabilities(engines=("infographic-remotion",), max_duration_ms=600_000, max_resolution=(1920, 1080))

    def render(self, request: RenderRequest) -> RenderResult:
        timeline = self._read_json(request.timeline_path, "timeline")
        document = self._read_json(request.storyboard_path, "storyboard")
        manifest = self._read_json(request.illustration_manifest_path, "illustration-manifest")
        try:
            storyboard = InfographicStoryboard.from_dict(document.get("infographic_storyboard", document))
        except (InfographicContractError, KeyError, TypeError, ValueError) as exc:
            raise RemotionRenderError(exc.code if isinstance(exc, InfographicContractError) else "STORYBOARD_INVALID", "storyboard 不符合 P1 契约") from exc
        try:
            props = InfographicStoryboardAdapter().to_remotion_props(storyboard, illustrations=self._illustrations(manifest), audio_paths=timeline.get("audio_paths"))
        except StoryboardConversionError as exc:
            raise RemotionRenderError(exc.code, "storyboard 转换失败") from exc
        run_dir = self._run_dir(request.timeline_path)
        self._assert_private_output(request.output_dir, run_dir)
        request.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = request.output_dir / "infographic.mp4"
        private_dir = run_dir / ".remotion-private"
        private_dir.mkdir(mode=0o700, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix="remotion-props-", encoding="utf-8", delete=False, dir=private_dir) as stream:
            props_path = Path(stream.name); json.dump(props, stream, ensure_ascii=False)
        started = time.monotonic()
        try:
            command = [self._node, str(self._render_mjs), str(props_path), str(output_path), str(run_dir)]
            try: completed = self._run(command, capture_output=True, text=True, timeout=self._timeout)
            except subprocess.TimeoutExpired as exc: raise RemotionRenderError("RENDER_TIMEOUT", f"Remotion 渲染超时（{self._timeout}秒）") from exc
            except FileNotFoundError as exc: raise RemotionRenderError("NODE_NOT_FOUND", "Node 可执行文件未找到") from exc
            if completed.returncode != 0: raise RemotionRenderError("RENDER_FAILED", f"Remotion 渲染失败 (exit {completed.returncode}): {self._sanitize_error(completed.stderr or completed.stdout or '')}")
        finally:
            props_path.unlink(missing_ok=True)
        if not output_path.is_file() or output_path.stat().st_size <= 0: raise RemotionRenderError("MP4_MISSING", "Remotion 未生成非空 MP4")
        try:
            probe = self._probe_mp4(output_path, int(props["width"]), int(props["height"]))
        except RemotionRenderError:
            output_path.unlink(missing_ok=True)
            raise
        return RenderResult(output_path=output_path, duration_ms=storyboard.total_duration_ms, frames=duration_frames(storyboard.total_duration_ms, int(props["fps"])), request_id=request.request_id, provider_metadata={"engine": "infographic-remotion", "page_count": len(storyboard.pages), "render_ms": int((time.monotonic()-started)*1000), "output_size_bytes": output_path.stat().st_size, "probe": probe})

    @staticmethod
    def _read_json(path: Path, label: str) -> dict[str, Any]:
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc: raise RemotionRenderError("ARTIFACT_NOT_FOUND", f"{label} 文件不存在") from exc
        except (OSError, json.JSONDecodeError) as exc: raise RemotionRenderError("ARTIFACT_READ_ERROR", f"{label} 文件读取失败") from exc
        if not isinstance(value, dict): raise RemotionRenderError("ARTIFACT_READ_ERROR", f"{label} 必须为 JSON object")
        return value

    @staticmethod
    def _run_dir(timeline_path: Path) -> Path:
        artifacts = next((parent for parent in timeline_path.parents if parent.name == "artifacts"), None)
        if artifacts is None: raise RemotionRenderError("ARTIFACT_DIR_NOT_FOUND", "无法从 timeline 路径解析 artifacts 目录")
        return artifacts.parent

    @staticmethod
    def _assert_private_output(output_dir: Path, run_dir: Path) -> None:
        try: output_dir.resolve().relative_to(run_dir.resolve())
        except ValueError as exc: raise RemotionRenderError("OUTPUT_PATH_FORBIDDEN", "renderer 输出必须位于当前 run") from exc

    @staticmethod
    def _illustrations(document: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in document.get("illustrations", []):
            if not isinstance(item, dict) or not isinstance(item.get("visual_id"), str) or not isinstance(item.get("image_path"), str): raise RemotionRenderError("ILLUSTRATION_MANIFEST_INVALID", "illustration manifest 无效")
            result[item["visual_id"]] = item["image_path"]
        return result

    def _probe_mp4(self, output_path: Path, expected_width: int, expected_height: int) -> dict[str, Any]:
        command = [self._ffprobe, "-v", "error", "-show_entries", "format=format_name,duration:stream=codec_type,width,height", "-of", "json", str(output_path)]
        try: completed = self._probe(command, capture_output=True, text=True, timeout=self._timeout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc: raise RemotionRenderError("FFPROBE_INVALID", "ffprobe 不可用或超时") from exc
        if completed.returncode != 0: raise RemotionRenderError("FFPROBE_INVALID", "ffprobe 无法验证 MP4")
        try:
            value = json.loads(completed.stdout); duration = float(value["format"]["duration"]); video = next(x for x in value["streams"] if x.get("codec_type") == "video")
            width, height = int(video["width"]), int(video["height"])
            if not value["format"].get("format_name") or duration <= 0 or width <= 0 or height <= 0: raise ValueError
            if (width, height) != (expected_width, expected_height): raise RemotionRenderError("FFPROBE_DIMENSIONS_MISMATCH", "MP4 尺寸不符合 props 契约")
            return {"format": value["format"].get("format_name", ""), "duration": duration, "width": width, "height": height}
        except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc: raise RemotionRenderError("FFPROBE_INVALID", "ffprobe 输出无有效视频流") from exc

    @staticmethod
    def _safe_text(text: str) -> str:
        safe = re.sub(r"(?:[A-Za-z]:\\|/)[^\s\"]+", "<path>", text)
        safe = re.sub(r"(?i)(?:api[_-]?key|secret|token|password|authorization)\s*[:=]\s*\S+", "<redacted>", safe)
        return re.sub(r"(?i)bearer\s+\S+", "Bearer <redacted>", safe).strip()[:500]

    _sanitize_error = _safe_text
