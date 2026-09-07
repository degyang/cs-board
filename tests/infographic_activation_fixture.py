"""Self-contained V3-shaped activation fixture; never reads repository outputs."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


TASK = "task-m09-v2-fixture"
RUN = "run-m09-v2-fixture"
V3_RECEIPT = "docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_root(tmp_path: Path, *, service_fingerprint: str = "fixture-service") -> Path:
    """Build one complete, isolated accepted-run shape under ``tmp_path``.

    The only media operation is a controlled local ffmpeg color source.  The
    result is deliberately not placed beneath repository ``outputs/``.
    """
    root = tmp_path
    source = Path(__file__).parents[1]
    renderer = root / "video_renderer"
    renderer.mkdir(exist_ok=True)
    for name in ("render.mjs", "browser-resolver.mjs", "package-lock.json"):
        shutil.copy2(source / "video_renderer" / name, renderer / name)

    shutil.rmtree(root / "outputs", ignore_errors=True)
    run = root / "outputs" / TASK / "runs" / RUN
    artifacts = run / "artifacts"
    render = artifacts / "render"
    render.mkdir(parents=True)
    mp4 = render / "infographic.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30",
         "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)],
        capture_output=True, text=True, check=True, timeout=15,
    )
    current_probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(mp4)],
        capture_output=True, text=True, check=True, timeout=5,
    ).stdout)
    stream = next(value for value in current_probe["streams"] if value.get("codec_type") == "video")
    probe = {
        "format": current_probe["format"]["format_name"],
        "duration": float(current_probe["format"]["duration"]),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
    }
    probe_path = render / "ffprobe.json"
    probe_path.write_text(json.dumps(probe))

    task_path = root / "outputs" / TASK / "task.json"
    task_path.write_text(json.dumps({
        "task_id": TASK, "active_run_id": RUN, "status": "succeeded", "engine": "infographic-remotion",
    }))
    run_path = run / "run.json"
    run_path.write_text(json.dumps({
        "task_id": TASK, "run_id": RUN, "status": "succeeded",
        "stages": {"render-visuals": {"status": "succeeded"}},
    }))
    manifest_path = render / "render-manifest.json"
    manifest_path.write_text(json.dumps({
        "task_id": TASK, "run_id": RUN, "output_relative_path": "artifacts/render/infographic.mp4",
        "output_sha256": sha(mp4), "probe_sha256": sha(probe_path), "size_bytes": mp4.stat().st_size,
        "duration_ms": max(1, round(probe["duration"] * 1000)), "frames": 3,
    }))
    index_path = artifacts / "index.json"
    index_path.write_text(json.dumps({"artifacts": {
        "render.video": _entry("render.video", "render/infographic.mp4", mp4),
        "render.ffprobe": _entry("render.ffprobe", "render/ffprobe.json", probe_path),
        "render.manifest": _entry("render.manifest", "render/render-manifest.json", manifest_path),
    }}))
    write_pointer(root, service_fingerprint=service_fingerprint)
    return root


def write_pointer(root: Path, *, service_fingerprint: str) -> None:
    run = root / "outputs" / TASK / "runs" / RUN
    artifacts = run / "artifacts"
    paths = {
        "task": root / "outputs" / TASK / "task.json", "run": run / "run.json",
        "mp4": artifacts / "render/infographic.mp4", "index": artifacts / "index.json",
        "manifest": artifacts / "render/render-manifest.json",
    }
    pointer = {
        "schema_version": 1, "verified_at": datetime.now(UTC).isoformat(),
        "task_id": TASK, "run_id": RUN, "run_relative_path": f"outputs/{TASK}/runs/{RUN}",
        "task_sha256": sha(paths["task"]), "run_sha256": sha(paths["run"]),
        "mp4_sha256": sha(paths["mp4"]), "artifact_index_sha256": sha(paths["index"]),
        "render_manifest_sha256": sha(paths["manifest"]), "v3_receipt": V3_RECEIPT,
        "v3_receipt_sha256": "", "service_fingerprint": service_fingerprint,
        "toolchain": {
            "renderer_sha256": sha(root / "video_renderer/render.mjs"),
            "browser_resolver_sha256": sha(root / "video_renderer/browser-resolver.mjs"),
            "lockfile_sha256": sha(root / "video_renderer/package-lock.json"),
            "node": "v-test", "remotion": "4.0.515", "browser": "Chrome fixture",
            "ffmpeg": "ffmpeg fixture", "ffprobe": "ffprobe fixture",
        },
    }
    receipt = root / V3_RECEIPT
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("Verdict: **PASS**\n" + "\n".join(pointer[key] for key in (
        "task_id", "run_id", "mp4_sha256", "artifact_index_sha256", "render_manifest_sha256",
    )))
    pointer["v3_receipt_sha256"] = sha(receipt)
    target = root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
    target.write_text(json.dumps(pointer))


def _entry(key: str, relative_path: str, path: Path) -> dict[str, object]:
    return {
        "artifact_key": key, "producer_stage": "render-visuals", "relative_path": relative_path,
        "sha256": sha(path), "size_bytes": path.stat().st_size, "status": "succeeded",
    }
