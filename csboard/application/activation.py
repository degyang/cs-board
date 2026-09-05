"""Fail-closed P3b activation verification for the single P6 smoke package."""
from __future__ import annotations

import hashlib
import subprocess
import os
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REASONS = ("READINESS_FAILED", "EVIDENCE_MISSING", "EVIDENCE_EXPIRED", "MP4_MISSING",
           "FFPROBE_INVALID", "MANIFEST_INVALID", "HASH_MISMATCH", "TOOLCHAIN_CHANGED",
           "SERVICE_PROBE_CHANGED")


class ActivationVerifier:
    """Read evidence afresh on every call; never renders or writes a package."""
    def __init__(self, project_root: Path, now: Any = None, current_service_fingerprint: str | None = None, browser_executable: str | None = None, runner: Any = None) -> None:
        self.root, self.now = Path(project_root), now or (lambda: datetime.now(UTC))
        self.current_service_fingerprint = current_service_fingerprint
        self.browser_executable = browser_executable or os.environ.get("CSBOARD_ACTIVATION_BROWSER")
        self.runner = runner or subprocess.run

    def verify(self, bootstrap_ready: bool) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        def check(name: str, ready: bool, code: str) -> bool:
            checks.append({"component": name, "ready": ready, "reason_code": None if ready else code}); return ready
        check("current-bootstrap", bootstrap_ready, "READINESS_FAILED")
        # No directory discovery: activation accepts only the operator-owned
        # pointer and rejects traversal or a missing pointer.
        try:
            pointer = json.loads((self.root / "outputs" / "remotion-activation-pointer.json").read_text())
            relative = Path(str(pointer["run_relative_path"])); task_id = str(pointer["task_id"]); run_id = str(pointer["run_id"])
            if not isinstance(pointer.get("verifier_receipt"), str) or not pointer["verifier_receipt"].startswith("docs/workmates/receipts/"):
                raise ValueError
            browser = str(pointer.get("browser_executable") or self.browser_executable)
            if not browser:
                raise ValueError
            self.browser_executable = browser
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError
            run = (self.root / "outputs" / relative).resolve()
            run.relative_to((self.root / "outputs").resolve())
        except (OSError, ValueError, KeyError, TypeError):
            run = None
        check("evidence-pointer", run is not None, "EVIDENCE_MISSING")
        if run is None:
            return self._result(checks)
        try:
            package_root = run.parents[1]
            task = json.loads((package_root / "task.json").read_text()); package = json.loads((package_root / "task-package.json").read_text()); run_doc = json.loads((run / "run.json").read_text())
            identity_ok = (task.get("task_id") == task_id and task.get("active_run_id") == run_id and task.get("status") == "succeeded"
                           and run_doc.get("task_id") == task_id and run_doc.get("run_id") == run_id and run_doc.get("status") == "succeeded"
                           and run_doc.get("stages", {}).get("render-visuals", {}).get("status") == "succeeded"
                           and package.get("schema_version") == 1 and package.get("package_kind") == "csboard-task-package"
                           and package.get("task_id") == task_id and package.get("runs_dir") == "runs")
        except (OSError, ValueError): identity_ok = False
        check("package-identity", identity_ok, "MANIFEST_INVALID")
        receipt_text = ""
        try:
            receipt = self.root / str(pointer["verifier_receipt"])
            receipt_text = receipt.read_text(encoding="utf-8")
            receipt_ok = (receipt.name == "M09-INFRA-REAL-006-V.md" and receipt.is_file()
                          and "结论：**PASS**" in receipt_text and task_id in receipt_text and run_id in receipt_text)
        except (OSError, KeyError, TypeError, ValueError): receipt_ok = False
        check("verifier-receipt", receipt_ok, "MANIFEST_INVALID")
        evidence_path = run / "evidence" / "remotion-real-smoke.json"
        try: evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, ValueError): evidence = None
        check("evidence", isinstance(evidence, dict), "EVIDENCE_MISSING")
        if not isinstance(evidence, dict): return self._result(checks)
        # Receipt binding is deliberately checked against the *current*
        # evidence values, not merely its filename or a loose PASS substring.
        receipt_ok = bool(receipt_ok and evidence.get("mp4_sha256") in receipt_text)
        for field in ("render_manifest_sha256", "artifact_index_sha256"):
            if evidence.get(field) in receipt_text:
                continue
            receipt_ok = False
        checks[3] = {"component": "verifier-receipt", "ready": receipt_ok,
                     "reason_code": None if receipt_ok else "MANIFEST_INVALID"}
        try:
            from csboard.domain.infographic import RemotionEvidenceV1
            required = {"schema_version", "verified_at", "renderer_sha256", "lockfile_sha256", "props_sha256", "tool_versions", "service_probe_sha256", "artifact_index_sha256", "render_manifest_sha256", "mp4_sha256", "artifact_refs", "ffprobe"}
            RemotionEvidenceV1(evidence["verified_at"], evidence["renderer_sha256"], evidence["lockfile_sha256"], evidence["props_sha256"], evidence["tool_versions"], evidence["service_probe_sha256"], evidence["artifact_index_sha256"], evidence["render_manifest_sha256"], evidence["mp4_sha256"], evidence["schema_version"]).to_dict()
            evidence_schema_ok = evidence.get("schema_version") == 1 and required <= set(evidence)
        except (KeyError, TypeError, ValueError): evidence_schema_ok = False
        check("evidence-schema", evidence_schema_ok, "MANIFEST_INVALID")
        try:
            verified = datetime.fromisoformat(str(evidence["verified_at"]).replace("Z", "+00:00"))
            fresh = verified.tzinfo is not None and self.now() - verified <= timedelta(hours=24) and self.now() >= verified
        except (KeyError, ValueError, TypeError): fresh = False
        check("evidence-freshness", fresh, "EVIDENCE_EXPIRED")
        index_path = run / "artifacts" / "index.json"; manifest_path = run / "artifacts" / "render" / "render-manifest.json"; mp4 = run / "artifacts" / "render" / "infographic.mp4"; probe_path = run / "artifacts" / "render" / "ffprobe.json"
        check("mp4", mp4.is_file() and mp4.stat().st_size > 0, "MP4_MISSING")
        try:
            probe = json.loads(probe_path.read_text())
            stream = next(item for item in probe.get("streams", []) if item.get("codec_type") == "video")
            duration = probe.get("duration", probe.get("duration_seconds", probe.get("format", {}).get("duration", 0)))
            summary = evidence.get("ffprobe", {})
            probe_ok = (float(duration) > 0 and stream.get("codec_name") == "h264"
                        and int(stream["width"]) == 1920 and int(stream["height"]) == 1080
                        and probe.get("format", {}).get("format_name") == summary.get("format")
                        and float(duration) == float(summary.get("duration_seconds"))
                        and int(stream["width"]) == int(summary.get("width")) and int(stream["height"]) == int(summary.get("height"))
                        and summary.get("video_codec") == "h264")
        except (OSError, ValueError, KeyError, TypeError, StopIteration): probe_ok = False
        check("ffprobe", probe_ok, "FFPROBE_INVALID")
        try:
            index_bytes = index_path.read_bytes(); index, manifest = json.loads(index_bytes), json.loads(manifest_path.read_text())
            refs = evidence["artifact_refs"]
            index_entries = index.get("artifacts", {})
            ref_entries = list(refs.values()) if isinstance(refs, dict) and all(isinstance(item, dict) for item in refs.values()) else []
            def exact_entry(entry: dict[str, Any]) -> bool:
                if not isinstance(entry, dict): return False
                key = entry.get("artifact_key")
                matches = [ref for ref in ref_entries if ref.get("artifact_key") == key]
                if len(matches) != 1: return False
                ref = matches[0]
                if any(entry.get(field) != ref.get(field) for field in ("artifact_key", "producer_stage", "relative_path", "sha256", "size_bytes", "status")): return False
                path = (run / "artifacts" / str(entry.get("relative_path", ""))).resolve()
                try:
                    path.relative_to((run / "artifacts").resolve())
                    return entry.get("status") == "succeeded" and path.is_file() and path.stat().st_size == entry.get("size_bytes")
                except OSError: return False
            index_full_ok = (isinstance(index_entries, dict) and len(index_entries) == len(ref_entries)
                             and set(index_entries) == {ref.get("artifact_key") for ref in ref_entries}
                             and all(exact_entry(entry) for entry in index_entries.values()))
            manifest_ok = (isinstance(index.get("artifacts"), dict) and isinstance(manifest, dict)
                           and hashlib.sha256(index_bytes).hexdigest() == evidence.get("artifact_index_sha256")
                           and index_full_ok
                           and all(key in refs for key in ("mp4", "probe", "manifest", "props"))
                           and manifest.get("output_relative_path") == "artifacts/" + refs["mp4"].get("relative_path", "")
                           and manifest.get("output_sha256") == evidence.get("mp4_sha256") == refs["mp4"].get("sha256")
                           and manifest.get("probe_sha256") == refs["probe"].get("sha256")
                           and manifest.get("size_bytes") == refs["mp4"].get("size_bytes")
                           and manifest.get("duration_ms", 0) > 0 and manifest.get("frames", 0) > 0)
        except (OSError, ValueError, KeyError, TypeError, AttributeError): manifest_ok = False; refs = {}
        check("manifest-index", manifest_ok, "MANIFEST_INVALID")
        hashes_ok = manifest_ok
        if isinstance(refs, dict):
            for entry in index.get("artifacts", {}).values() if isinstance(index, dict) else ():
                try:
                    path = (run / "artifacts" / str(entry["relative_path"])).resolve()
                    hashes_ok &= (path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"])
                except (OSError, KeyError, TypeError): hashes_ok = False
        for key, expected in (("mp4", evidence.get("mp4_sha256")), ("probe", evidence.get("artifact_refs", {}).get("probe", {}).get("sha256")), ("manifest", evidence.get("render_manifest_sha256")), ("props", evidence.get("props_sha256"))):
            item = refs.get(key, {}) if isinstance(refs, dict) else {}
            if not isinstance(item, dict): hashes_ok = False; continue
            path = run / "artifacts" / str(item.get("relative_path", ""))
            try: hashes_ok &= path.resolve().is_relative_to((run / "artifacts").resolve()) and hashlib.sha256(path.read_bytes()).hexdigest() == expected == item.get("sha256")
            except OSError: hashes_ok = False
        check("artifact-hashes", hashes_ok, "HASH_MISMATCH")
        renderer = self.root / "video_renderer" / "render.mjs"; lockfile = self.root / "video_renderer" / "package-lock.json"
        try:
            versions = evidence.get("tool_versions", {})
            def version(command: list[str]) -> str:
                result = self.runner(command, capture_output=True, text=True, timeout=5)
                if result.returncode != 0: raise OSError
                return result.stdout.splitlines()[0].strip()
            lock = json.loads(lockfile.read_text())
            remotion = str(lock.get("packages", {}).get("node_modules/remotion", {}).get("version", ""))
            if not remotion: raise OSError
            actual = {"node": version(["node", "--version"]), "remotion": remotion,
                      "browser": version([str(self.browser_executable), "--version"]),
                      "ffmpeg": version(["ffmpeg", "-version"]), "ffprobe": version(["ffprobe", "-version"])}
            tools_ok = (hashlib.sha256(renderer.read_bytes()).hexdigest() == evidence.get("renderer_sha256") and hashlib.sha256(lockfile.read_bytes()).hexdigest() == evidence.get("lockfile_sha256")
                        and all(actual[key] == versions.get(key) for key in actual))
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, FileNotFoundError): tools_ok = False
        check("current-toolchain", tools_ok, "TOOLCHAIN_CHANGED")
        # P6 must carry an independently reviewed expected safe fingerprint;
        # absence is intentionally not inferred from its smoke-local scope.
        service_ok = (isinstance(evidence.get("expected_service_fingerprint"), str)
                      and isinstance(self.current_service_fingerprint, str)
                      and evidence["expected_service_fingerprint"] == self.current_service_fingerprint)
        check("current-service-probes", service_ok, "SERVICE_PROBE_CHANGED")
        return self._result(checks)

    @staticmethod
    def _result(checks: list[dict[str, Any]]) -> dict[str, Any]:
        failure = next((item for item in checks if not item["ready"]), None)
        return {"supported": failure is None, "reason_code": None if failure is None else failure["reason_code"], "diagnostics": checks}
