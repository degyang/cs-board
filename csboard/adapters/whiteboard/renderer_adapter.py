"""Whiteboard renderer adapter — wraps render_stream_whiteboard.py.

Implements RendererPort by calling the existing whiteboard render script
for each Visual Item.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from csboard.domain.provider_types import (
    RenderRequest,
    RenderResult,
    RendererCapabilities,
)


class WhiteboardRendererAdapter:
    """RendererPort implementation using the whiteboard render script.

    Parameters
    ----------
    render_script:
        Path to ``render_stream_whiteboard.py``.
    python_bin:
        Python interpreter to use.
    timeout:
        Per-clip render timeout in seconds.
    """

    def __init__(
        self,
        render_script: Path | str | None = None,
        python_bin: str = "python3",
        timeout: float = 300.0,
    ) -> None:
        if render_script is None:
            render_script = Path(__file__).resolve().parents[2] / "scripts" / "render_stream_whiteboard.py"
        self._script = str(render_script)
        self._python = python_bin
        self._timeout = timeout

    def render(self, request: RenderRequest) -> RenderResult:
        """Render video clips for all Visual Items.

        Reads timeline, storyboard, and illustration manifest, then renders
        each Visual Item as a separate clip using the whiteboard renderer.
        """
        # Read input artifacts
        timeline = self._read_json(request.timeline_path)
        storyboard = self._read_json(request.storyboard_path)
        illustration_manifest = self._read_json(request.illustration_manifest_path)

        # Build lookup maps
        visuals_by_id = {v["visual_id"]: v for v in storyboard.get("visuals", [])}
        illustrations_by_id = {
            i["visual_id"]: i for i in illustration_manifest.get("illustrations", [])
        }

        # Create output directory
        clips_dir = request.output_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)

        # Render each visual
        clips: list[dict[str, Any]] = []
        total_duration_ms = 0
        total_frames = 0

        for unit in timeline.get("units", []):
            for vt in unit.get("visual_timings", []):
                visual_id = vt["visual_id"]
                start_ms = vt["start_ms"]
                end_ms = vt["end_ms"]
                duration_ms = end_ms - start_ms

                visual = visuals_by_id.get(visual_id, {})
                illustration = illustrations_by_id.get(visual_id, {})

                # Get image path
                image_path = illustration.get("image_path", "")
                if not image_path:
                    continue

                # Resolve image path relative to project root
                # timeline_path is at: projects/<proj>/runs/<run>/artifacts/timeline.json
                # So parents[3] is the project root
                project_root = request.timeline_path.parents[3]
                full_image_path = project_root / image_path

                if not full_image_path.exists():
                    continue

                # Generate annotation for this visual
                annotation = self._build_annotation(visual, duration_ms)

                # Render clip
                clip_path = clips_dir / f"{visual_id}.mp4"
                self._render_clip(full_image_path, annotation, clip_path, duration_ms)

                if clip_path.exists():
                    # Make clip path relative to project root
                    try:
                        clip_relative = clip_path.relative_to(project_root)
                    except ValueError:
                        clip_relative = clip_path
                    clips.append({
                        "visual_id": visual_id,
                        "unit_id": unit["unit_id"],
                        "clip_path": str(clip_relative),
                        "duration_ms": duration_ms,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                    })
                    total_duration_ms += duration_ms
                    total_frames += max(1, duration_ms * 30 // 1000)  # Assume 30fps

        # Create a concatenated master (placeholder - real implementation would use ffmpeg)
        master_path = request.output_dir / "silent_master.mp4"
        master_path.write_bytes(b"\x00" * 128)  # Placeholder

        return RenderResult(
            output_path=master_path,
            duration_ms=total_duration_ms,
            frames=total_frames,
            request_id=request.request_id,
            provider_metadata={"clips": clips},
        )

    def capabilities(self) -> RendererCapabilities:
        return RendererCapabilities(
            engines=("whiteboard",),
            max_duration_ms=300_000,
            max_resolution=(1920, 1080),
        )

    def _build_annotation(self, visual: dict[str, Any], duration_ms: int) -> dict[str, Any]:
        """Build a simple annotation for the whiteboard renderer."""
        return {
            "canvas": {"width": 1920, "height": 1080},
            "sceneDurationMs": duration_ms,
            "sequence": [
                {
                    "id": visual.get("visual_id", "region-1"),
                    "startMs": 0,
                    "region": {"x": 100, "y": 100, "width": 1720, "height": 880},
                }
            ],
        }

    def _render_clip(
        self,
        image_path: Path,
        annotation: dict[str, Any],
        output_path: Path,
        duration_ms: int,
    ) -> None:
        """Render a single clip using the whiteboard render script."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(annotation, f, ensure_ascii=False)
            annotation_path = Path(f.name)

        try:
            result = subprocess.run(
                [
                    self._python,
                    self._script,
                    str(image_path),
                    str(annotation_path),
                    str(output_path),
                    "--total-ms",
                    str(duration_ms),
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Whiteboard render failed: {result.stderr[:500] or result.stdout[:500]}"
                )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Whiteboard render timed out after {self._timeout}s"
            ) from exc
        finally:
            annotation_path.unlink(missing_ok=True)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read a JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))
