"""Read-only, fail-closed activation verification for the accepted M09 V3 run."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

REASONS = ("READINESS_FAILED", "EVIDENCE_MISSING", "EVIDENCE_EXPIRED", "MP4_MISSING", "FFPROBE_INVALID", "MANIFEST_INVALID", "HASH_MISMATCH", "TOOLCHAIN_CHANGED", "SERVICE_PROBE_CHANGED")
_POINTER = "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
_V3_RECEIPT = "docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md"


class ActivationVerifier:
    """Revalidate one operator-owned pointer; never discovers, renders, or writes."""
    def __init__(self, project_root: Path, *, now: Callable[[], datetime] | None = None,
                 current_service_fingerprint: str | None = None, runner: Any = None,
                 browser_version: Callable[[], str] | None = None) -> None:
        self.root = Path(project_root).resolve()
        self.now = now or (lambda: datetime.now(UTC))
        self.current_service_fingerprint, self.runner = current_service_fingerprint, runner or subprocess.run
        self.browser_version = browser_version or self._configured_browser_version

    def verify(self, bootstrap_ready: bool) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        def check(component: str, ready: bool, code: str) -> None:
            checks.append({"component": component, "ready": bool(ready), "reason_code": None if ready else code})
        check("current-bootstrap", bootstrap_ready, "READINESS_FAILED")
        pointer = self._read_pointer()
        check("activation-pointer", pointer is not None, "EVIDENCE_MISSING")
        if pointer is None:
            return self._result(checks)
        run = self._run_path(pointer)
        check("accepted-identity", run is not None, "MANIFEST_INVALID")
        check("v3-verdict", self._v3_receipt_ok(pointer), "MANIFEST_INVALID")
        check("evidence-freshness", self._fresh(pointer.get("verified_at")), "EVIDENCE_EXPIRED")
        if run is None:
            return self._result(checks)
        paths = self._paths(run)
        check("task-run-stage", self._identity_ok(paths, pointer), "MANIFEST_INVALID")
        check("mp4", paths["mp4"].is_file() and paths["mp4"].stat().st_size > 0, "MP4_MISSING")
        check("ffprobe", self._probe_ok(paths), "FFPROBE_INVALID")
        check("manifest-index", self._manifest_ok(paths, pointer), "MANIFEST_INVALID")
        check("artifact-hashes", self._hashes_ok(paths, pointer), "HASH_MISMATCH")
        check("current-toolchain", self._toolchain_ok(pointer), "TOOLCHAIN_CHANGED")
        service_ok = isinstance(pointer.get("service_fingerprint"), str) and pointer["service_fingerprint"] == self.current_service_fingerprint
        check("current-service-prerequisites", service_ok, "SERVICE_PROBE_CHANGED")
        return self._result(checks)

    def _read_pointer(self) -> dict[str, Any] | None:
        try:
            value = json.loads((self.root / _POINTER).read_text(encoding="utf-8"))
            required = {"schema_version", "verified_at", "task_id", "run_id", "run_relative_path", "task_sha256", "run_sha256", "mp4_sha256", "artifact_index_sha256", "render_manifest_sha256", "v3_receipt", "v3_receipt_sha256", "toolchain", "service_fingerprint"}
            if not isinstance(value, dict) or value.get("schema_version") != 1 or required - set(value) or value.get("v3_receipt") != _V3_RECEIPT:
                return None
            if not isinstance(value.get("toolchain"), dict) or not all(isinstance(value.get(key), str) for key in required - {"schema_version", "toolchain"}):
                return None
            return value
        except (OSError, ValueError, TypeError):
            return None

    def _run_path(self, pointer: dict[str, Any]) -> Path | None:
        try:
            relative = Path(pointer["run_relative_path"])
            expected = Path("outputs") / pointer["task_id"] / "runs" / pointer["run_id"]
            if relative != expected or relative.is_absolute() or ".." in relative.parts:
                return None
            run = (self.root / relative).resolve(); run.relative_to((self.root / "outputs").resolve())
            return run
        except (ValueError, TypeError):
            return None

    def _v3_receipt_ok(self, pointer: dict[str, Any]) -> bool:
        try:
            receipt = self.root / _V3_RECEIPT; text = receipt.read_text(encoding="utf-8")
            bindings = (pointer["task_id"], pointer["run_id"], pointer["mp4_sha256"], pointer["artifact_index_sha256"], pointer["render_manifest_sha256"])
            return receipt.is_file() and self._sha(receipt) == pointer["v3_receipt_sha256"] and "Verdict: **PASS**" in text and all(value in text for value in bindings)
        except (OSError, TypeError, KeyError):
            return False

    @staticmethod
    def _paths(run: Path) -> dict[str, Path]:
        artifacts = run / "artifacts"
        return {"task": run.parents[1] / "task.json", "run": run / "run.json", "index": artifacts / "index.json", "manifest": artifacts / "render" / "render-manifest.json", "mp4": artifacts / "render" / "infographic.mp4", "probe": artifacts / "render" / "ffprobe.json"}

    def _identity_ok(self, paths: dict[str, Path], pointer: dict[str, Any]) -> bool:
        try:
            task, run = (json.loads(paths[key].read_text(encoding="utf-8")) for key in ("task", "run"))
            return task.get("task_id") == pointer["task_id"] and task.get("active_run_id") == pointer["run_id"] and task.get("status") == "succeeded" and task.get("engine") == "infographic-remotion" and run.get("task_id") == pointer["task_id"] and run.get("run_id") == pointer["run_id"] and run.get("status") == "succeeded" and run.get("stages", {}).get("render-visuals", {}).get("status") == "succeeded"
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def _probe_ok(self, paths: dict[str, Path]) -> bool:
        try:
            stored = json.loads(paths["probe"].read_text(encoding="utf-8"))
            # ffprobe pretty-prints JSON by default.  Preserve the complete
            # stdout here; _command's normal first-line behavior is only for
            # version probes.
            current = json.loads(self._command(
                ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(paths["mp4"])],
                first_line=False,
            ))
            stream = next(item for item in current["streams"] if item.get("codec_type") == "video")
            return stream.get("codec_name") == "h264" and int(stream["width"]) == 1920 and int(stream["height"]) == 1080 and float(current["format"]["duration"]) > 0 and stored.get("format") == current["format"].get("format_name") and float(stored.get("duration")) == float(current["format"]["duration"]) and int(stored.get("width")) == int(stream["width"]) and int(stored.get("height")) == int(stream["height"])
        except (OSError, ValueError, TypeError, KeyError, StopIteration, subprocess.TimeoutExpired):
            return False

    def _manifest_ok(self, paths: dict[str, Path], pointer: dict[str, Any]) -> bool:
        try:
            index, manifest = json.loads(paths["index"].read_text()), json.loads(paths["manifest"].read_text())
            entries = index.get("artifacts"); required = {"render.video": ("render/infographic.mp4", pointer["mp4_sha256"]), "render.manifest": ("render/render-manifest.json", pointer["render_manifest_sha256"]), "render.ffprobe": ("render/ffprobe.json", None)}
            if not isinstance(entries, dict) or not all(key in entries for key in required): return False
            for key, (relative, digest) in required.items():
                entry = entries[key]
                if not isinstance(entry, dict) or entry.get("relative_path") != relative or entry.get("status") != "succeeded" or (digest and entry.get("sha256") != digest): return False
            return manifest.get("task_id") == pointer["task_id"] and manifest.get("run_id") == pointer["run_id"] and manifest.get("output_relative_path") == "artifacts/render/infographic.mp4" and manifest.get("output_sha256") == pointer["mp4_sha256"] and manifest.get("probe_sha256") == entries["render.ffprobe"].get("sha256") and manifest.get("size_bytes") == entries["render.video"].get("size_bytes") and manifest.get("duration_ms", 0) > 0 and manifest.get("frames", 0) > 0
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def _hashes_ok(self, paths: dict[str, Path], pointer: dict[str, Any]) -> bool:
        try:
            index = json.loads(paths["index"].read_text()); exact = {"task": pointer["task_sha256"], "run": pointer["run_sha256"], "index": pointer["artifact_index_sha256"], "manifest": pointer["render_manifest_sha256"], "mp4": pointer["mp4_sha256"]}
            if any(self._sha(paths[key]) != value for key, value in exact.items()): return False
            for entry in index.get("artifacts", {}).values():
                target = (paths["index"].parent / Path(str(entry["relative_path"]))).resolve(); target.relative_to(paths["index"].parent.resolve())
                if not target.is_file() or target.stat().st_size != entry["size_bytes"] or self._sha(target) != entry["sha256"]: return False
            return True
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def _toolchain_ok(self, pointer: dict[str, Any]) -> bool:
        try:
            expected = pointer["toolchain"]; renderer = self.root / "video_renderer" / "render.mjs"; resolver = self.root / "video_renderer" / "browser-resolver.mjs"; lockfile = self.root / "video_renderer" / "package-lock.json"; lock = json.loads(lockfile.read_text())
            actual = {"renderer_sha256": self._sha(renderer), "browser_resolver_sha256": self._sha(resolver), "lockfile_sha256": self._sha(lockfile), "node": self._command(["node", "--version"]), "remotion": str(lock["packages"]["node_modules/remotion"]["version"]), "browser": self.browser_version(), "ffmpeg": self._command(["ffmpeg", "-version"]), "ffprobe": self._command(["ffprobe", "-version"])}
            return all(isinstance(expected.get(key), str) and expected[key] == value for key, value in actual.items())
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _configured_browser_version(self) -> str:
        """Use the renderer's accepted browser resolver, never an env-only fork."""
        resolver = self.root / "video_renderer" / "browser-resolver.mjs"
        if not resolver.is_file():
            raise OSError("browser resolver unavailable")
        program = (
            f"import {{resolveBrowserExecutable}} from {resolver.as_uri()!r};"
            "import {execFileSync} from 'node:child_process';"
            "const executable = resolveBrowserExecutable();"
            "if (!executable) process.exit(2);"
            "process.stdout.write(execFileSync(executable, ['--version'], {encoding: 'utf8'}));"
        )
        return self._command(["node", "--input-type=module", "--eval", program])

    def _command(self, command: list[str], *, first_line: bool = True) -> str:
        result = self.runner(command, capture_output=True, text=True, timeout=5)
        if result.returncode != 0 or not result.stdout: raise OSError("command unavailable")
        return result.stdout.splitlines()[0].strip() if first_line else result.stdout

    @staticmethod
    def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

    def _fresh(self, raw: Any) -> bool:
        try:
            checked, now = datetime.fromisoformat(str(raw).replace("Z", "+00:00")), self.now()
            return checked.tzinfo is not None and now >= checked and now - checked <= timedelta(hours=24)
        except (TypeError, ValueError): return False

    @staticmethod
    def _result(checks: list[dict[str, Any]]) -> dict[str, Any]:
        failure = next((item for item in checks if not item["ready"]), None)
        return {"supported": failure is None, "reason_code": None if failure is None else failure["reason_code"], "diagnostics": checks}


def accepted_v3_gate(project_root: Path) -> bool:
    """Return only whether the operator-bound V3 verdict is currently intact.

    This is the explicit bootstrap gate used by runtime composition.  It is
    intentionally weaker than :meth:`ActivationVerifier.verify`; activation
    still rechecks freshness, state, artifacts, toolchain and services.
    """
    verifier = ActivationVerifier(project_root)
    pointer = verifier._read_pointer()
    return pointer is not None and verifier._v3_receipt_ok(pointer)
