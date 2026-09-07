"""M09 activation is bound to V3, not a mutable supported constant."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from csboard.application.activation import ActivationVerifier
from csboard.runtime.toolchain import bootstrap_diagnostics
from tests.infographic_activation_fixture import RUN, TASK, create_root, sha

NOW = datetime(2026, 9, 7, 12, tzinfo=UTC)


def _root(tmp_path: Path) -> Path:
    return create_root(tmp_path, verified_at=NOW)


def _runner(command, **_kwargs):
    if command[0] == "ffprobe" and "-show_streams" in command:
        payload = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080}], "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "2.0"}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload, indent=2))
    value = {"node": "v-test", "ffmpeg": "ffmpeg fixture", "ffprobe": "ffprobe fixture"}[command[0]]
    return SimpleNamespace(returncode=0, stdout=value + "\n")


def _verifier(root: Path, fingerprint: str = "fixture-service") -> ActivationVerifier:
    return ActivationVerifier(root, now=lambda: NOW, current_service_fingerprint=fingerprint, runner=_runner, browser_version=lambda: "Chrome fixture")


def test_v3_fixture_activates_and_bootstrap_is_the_same_projection(tmp_path: Path):
    root = _root(tmp_path)
    assert _verifier(root).verify(True)["supported"] is True
    assert _verifier(root).verify(False)["reason_code"] == "READINESS_FAILED"


def test_probe_accepts_real_multiline_ffprobe_json(tmp_path: Path):
    root = _root(tmp_path)
    run = root / "outputs" / TASK / "runs" / RUN
    # This invokes the installed ffprobe binary, whose default JSON is
    # pretty-printed over multiple lines; it is not a fake single-line result.
    assert ActivationVerifier(root)._probe_ok(ActivationVerifier._paths(run)) is True


def test_browser_version_uses_renderer_resolver_without_configured_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _root(tmp_path)
    home = tmp_path / "home"
    browser = home / ".cache/puppeteer/chrome-headless-shell/linux-999/chrome-headless-shell-linux64/chrome-headless-shell"
    browser.parent.mkdir(parents=True)
    browser.write_text("#!/bin/sh\necho Chrome resolver-fixture\n")
    browser.chmod(0o700)
    monkeypatch.setenv("HOME", str(home))
    for name in ("REMOTION_BROWSER_EXECUTABLE", "PUPPETEER_EXECUTABLE_PATH", "CHROME_PATH"):
        monkeypatch.delenv(name, raising=False)
    assert ActivationVerifier(root)._configured_browser_version() == "Chrome resolver-fixture"
    diagnostics = bootstrap_diagnostics(root, environ={})
    browser_check = next(item for item in diagnostics if item["component"] == "remotion-browser")
    assert browser_check == {"component": "remotion-browser", "ready": True, "reason_code": "BROWSER_UNAVAILABLE"}


@pytest.mark.parametrize("mutation, reason", [("pointer", "EVIDENCE_MISSING"), ("future", "EVIDENCE_EXPIRED"), ("run", "MANIFEST_INVALID"), ("mp4", "MP4_MISSING"), ("probe", "FFPROBE_INVALID"), ("manifest", "MANIFEST_INVALID"), ("hash", "HASH_MISMATCH"), ("tool", "TOOLCHAIN_CHANGED")])
def test_activation_fail_closed_matrix(tmp_path: Path, mutation: str, reason: str):
    root = _root(tmp_path); run = root / "outputs" / TASK / "runs" / RUN
    pointer = root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
    if mutation == "pointer": pointer.unlink()
    elif mutation == "future":
        value = json.loads(pointer.read_text()); value["verified_at"] = "2999-01-01T00:00:00Z"; pointer.write_text(json.dumps(value))
    elif mutation == "run":
        value = json.loads((run / "run.json").read_text()); value["status"] = "failed"; (run / "run.json").write_text(json.dumps(value))
    elif mutation == "mp4": (run / "artifacts/render/infographic.mp4").unlink()
    elif mutation == "probe": (run / "artifacts/render/ffprobe.json").write_text("{}")
    elif mutation == "manifest": (run / "artifacts/index.json").write_text("{}")
    elif mutation == "hash": (run / "artifacts/render/infographic.mp4").write_bytes(b"tampered")
    else: (root / "video_renderer/render.mjs").write_text("tampered")
    assert _verifier(root).verify(True)["reason_code"] == reason


def test_receipt_binding_service_change_and_repeated_read_fail_closed(tmp_path: Path):
    root = _root(tmp_path); receipt = root / "docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md"
    receipt.write_text("Verdict: **FAIL**")
    assert _verifier(root).verify(True)["reason_code"] == "MANIFEST_INVALID"
    root = _root(tmp_path)
    assert _verifier(root, "changed").verify(True)["reason_code"] == "SERVICE_PROBE_CHANGED"
    verifier = _verifier(root); assert verifier.verify(True)["supported"] is True
    value = json.loads((root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json").read_text()); value["verified_at"] = "2000-01-01T00:00:00Z"; (root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json").write_text(json.dumps(value))
    assert verifier.verify(True)["reason_code"] == "EVIDENCE_EXPIRED"


@pytest.mark.parametrize("mutation", ("missing", "not-pass", "task", "run", "hash"))
def test_receipt_must_remain_explicitly_passed_and_bound(tmp_path: Path, mutation: str):
    root = _root(tmp_path)
    receipt = root / "docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md"
    if mutation == "missing":
        receipt.unlink()
    elif mutation == "not-pass":
        receipt.write_text("Verdict: **FAIL**")
    elif mutation == "task":
        receipt.write_text(receipt.read_text().replace(TASK, "task-other"))
    elif mutation == "run":
        receipt.write_text(receipt.read_text().replace(RUN, "run-other"))
    else:
        receipt.write_text(receipt.read_text().replace(sha(root / "outputs" / TASK / "runs" / RUN / "artifacts/render/infographic.mp4"), "0" * 64))
    pointer = root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
    value = json.loads(pointer.read_text())
    value["v3_receipt_sha256"] = sha(receipt) if receipt.exists() else "0" * 64
    pointer.write_text(json.dumps(value))
    assert _verifier(root).verify(True)["reason_code"] == "MANIFEST_INVALID"


@pytest.mark.parametrize("mutation", ("entry", "missing-required", "wrong-path"))
def test_rebound_index_structure_remains_fail_closed(tmp_path: Path, mutation: str):
    root = _root(tmp_path)
    run = root / "outputs" / TASK / "runs" / RUN
    index_path = run / "artifacts/index.json"
    index = json.loads(index_path.read_text())
    if mutation == "entry":
        index["artifacts"]["render.video"] = "malformed"
    elif mutation == "missing-required":
        del index["artifacts"]["render.manifest"]
    else:
        index["artifacts"]["render.video"]["relative_path"] = "render/other.mp4"
    index_path.write_text(json.dumps(index))
    pointer = root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
    value = json.loads(pointer.read_text())
    previous_digest = value["artifact_index_sha256"]
    value["artifact_index_sha256"] = sha(index_path)
    receipt = root / "docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md"
    receipt.write_text(receipt.read_text().replace(previous_digest, value["artifact_index_sha256"]))
    value["v3_receipt_sha256"] = sha(receipt)
    pointer.write_text(json.dumps(value))
    assert _verifier(root).verify(True)["reason_code"] == "MANIFEST_INVALID"


@pytest.mark.parametrize("tool", ("node", "remotion", "browser", "ffmpeg", "ffprobe", "browser_resolver_sha256"))
def test_each_toolchain_binding_is_rechecked(tmp_path: Path, tool: str):
    root = _root(tmp_path)
    pointer = root / "docs/workmates/receipts/M09-ACTIVATE-001.pointer.json"
    value = json.loads(pointer.read_text())
    value["toolchain"][tool] = "changed"
    pointer.write_text(json.dumps(value))
    assert _verifier(root).verify(True)["reason_code"] == "TOOLCHAIN_CHANGED"
