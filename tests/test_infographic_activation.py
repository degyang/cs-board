from __future__ import annotations
import json, shutil
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest
from csboard.application.activation import ActivationVerifier

SOURCE = Path(__file__).parents[1]
BROWSER = "/home/ubuntu/.cache/puppeteer/chrome/linux-152.0.7977.54/chrome-linux64/chrome"

def _verifier(root: Path, fingerprint: str = "fixture-safe") -> ActivationVerifier:
    return ActivationVerifier(root, current_service_fingerprint=fingerprint, browser_executable=BROWSER)

def _root(tmp_path: Path) -> Path:
    shutil.copytree(SOURCE / "outputs" / "p6-real-smoke-51657b64d6d3", tmp_path / "outputs" / "p6-real-smoke-51657b64d6d3", dirs_exist_ok=True)
    shutil.copy2(SOURCE / "outputs" / "remotion-activation-pointer.json", tmp_path / "outputs" / "remotion-activation-pointer.json")
    (tmp_path / "docs/workmates/receipts").mkdir(parents=True, exist_ok=True); shutil.copy2(SOURCE / "docs/workmates/receipts/M09-INFRA-REAL-006-V.md", tmp_path / "docs/workmates/receipts/M09-INFRA-REAL-006-V.md")
    value=json.loads(_evidence(tmp_path).read_text()); value["expected_service_fingerprint"]="fixture-safe"; _evidence(tmp_path).write_text(json.dumps(value))
    (tmp_path / "video_renderer").mkdir(exist_ok=True); shutil.copy2(SOURCE / "video_renderer" / "render.mjs", tmp_path / "video_renderer" / "render.mjs"); shutil.copy2(SOURCE / "video_renderer" / "package-lock.json", tmp_path / "video_renderer" / "package-lock.json")
    return tmp_path

def _evidence(root: Path) -> Path: return root / "outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3/evidence/remotion-real-smoke.json"

def test_real_evidence_activates_and_bootstrap_regression_fails_closed(tmp_path: Path):
    root=_root(tmp_path); verifier=_verifier(root)
    assert verifier.verify(True)["supported"] is True
    value=verifier.verify(False); assert value["supported"] is False and value["reason_code"] == "READINESS_FAILED"

def test_missing_pointer_future_evidence_and_restart_are_fail_closed_or_fresh(tmp_path: Path):
    root=_root(tmp_path); (root / "outputs/remotion-activation-pointer.json").unlink()
    assert _verifier(root).verify(True)["reason_code"] == "EVIDENCE_MISSING"
    root=_root(tmp_path); value=json.loads(_evidence(root).read_text()); value["verified_at"]="2999-01-01T00:00:00Z"; _evidence(root).write_text(json.dumps(value))
    assert _verifier(root).verify(True)["reason_code"] == "EVIDENCE_EXPIRED"
    root=_root(tmp_path); assert _verifier(root).verify(True) == _verifier(root).verify(True)

@pytest.mark.parametrize("mutation,reason", [("stale","EVIDENCE_EXPIRED"),("mp4","MP4_MISSING"),("probe","FFPROBE_INVALID"),("manifest","MANIFEST_INVALID"),("hash","HASH_MISMATCH"),("tool","TOOLCHAIN_CHANGED")])
def test_activation_tamper_matrix(tmp_path: Path, mutation: str, reason: str):
    root=_root(tmp_path)
    run=root / "outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3"
    if mutation == "stale":
        value=json.loads(_evidence(root).read_text()); value["verified_at"]="2000-01-01T00:00:00Z"; _evidence(root).write_text(json.dumps(value))
    elif mutation == "mp4": (run / "artifacts/render/infographic.mp4").unlink()
    elif mutation == "probe": (run / "artifacts/render/ffprobe.json").write_text("{}")
    elif mutation == "manifest": (run / "artifacts/index.json").write_text("{}")
    elif mutation == "hash":
        target = run / "artifacts/render/infographic.mp4"; target.write_bytes(b"x" * target.stat().st_size)
    else: (root / "video_renderer/render.mjs").write_text("changed")
    result=_verifier(root).verify(True); assert result["supported"] is False and result["reason_code"] == reason

def test_service_fingerprint_change_is_a_distinct_fail_closed_reason(tmp_path: Path):
    root=_root(tmp_path)
    result=_verifier(root, "changed").verify(True)
    assert result["supported"] is False and result["reason_code"] == "SERVICE_PROBE_CHANGED"

def test_recomputed_index_hash_cannot_hide_entry_mismatch(tmp_path: Path):
    root=_root(tmp_path); index_path=root / "outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3/artifacts/index.json"
    index=json.loads(index_path.read_text()); index["artifacts"]["render.mp4"]["size_bytes"] = 1
    index_path.write_text(json.dumps(index)); evidence=json.loads(_evidence(root).read_text())
    evidence["artifact_index_sha256"] = hashlib.sha256(index_path.read_bytes()).hexdigest(); _evidence(root).write_text(json.dumps(evidence))
    result=_verifier(root).verify(True)
    assert result["supported"] is False and result["reason_code"] == "MANIFEST_INVALID"

@pytest.mark.parametrize("target", ("entry", "ref"))
def test_malformed_index_or_evidence_ref_is_manifest_invalid(tmp_path: Path, target: str):
    root=_root(tmp_path); index_path=root / "outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3/artifacts/index.json"
    evidence=json.loads(_evidence(root).read_text())
    if target == "entry":
        index=json.loads(index_path.read_text()); index["artifacts"]["render.mp4"] = "malformed"; index_path.write_text(json.dumps(index)); evidence["artifact_index_sha256"] = hashlib.sha256(index_path.read_bytes()).hexdigest()
    else: evidence["artifact_refs"]["mp4"] = "malformed"
    _evidence(root).write_text(json.dumps(evidence))
    result=_verifier(root).verify(True)
    assert result["supported"] is False and result["reason_code"] == "MANIFEST_INVALID"

@pytest.mark.parametrize("mutation", ("extra", "missing", "ref-path", "package"))
def test_full_binding_structural_tamper_is_manifest_invalid(tmp_path: Path, mutation: str):
    root=_root(tmp_path); run=root / "outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3"; index_path=run / "artifacts/index.json"; evidence=json.loads(_evidence(root).read_text())
    index=json.loads(index_path.read_text())
    if mutation == "extra": index["artifacts"]["extra"] = dict(index["artifacts"]["render.mp4"]); index["artifacts"]["extra"]["artifact_key"]="extra"
    elif mutation == "missing": del index["artifacts"]["render.props"]
    elif mutation == "ref-path": evidence["artifact_refs"]["mp4"]["relative_path"]="render/other.mp4"
    else:
        package=root / "outputs/p6-real-smoke-51657b64d6d3/task-package.json"; value=json.loads(package.read_text()); value["runs_dir"]="other"; package.write_text(json.dumps(value))
    if mutation != "package": index_path.write_text(json.dumps(index)); evidence["artifact_index_sha256"] = hashlib.sha256(index_path.read_bytes()).hexdigest()
    _evidence(root).write_text(json.dumps(evidence))
    assert _verifier(root).verify(True)["reason_code"] == "MANIFEST_INVALID"

@pytest.mark.parametrize("mutation", ("hash", "not-pass"))
def test_receipt_must_bind_evidence_hash_and_explicit_pass(tmp_path: Path, mutation: str):
    root=_root(tmp_path); receipt=root / "docs/workmates/receipts/M09-INFRA-REAL-006-V.md"
    text=receipt.read_text()
    if mutation == "hash": text=text.replace("18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a", "0" * 64)
    else: text=text.replace("结论：**PASS**", "结论：**NOT PASS**")
    receipt.write_text(text)
    assert _verifier(root).verify(True)["reason_code"] == "MANIFEST_INVALID"

@pytest.mark.parametrize("tool", ("node", "remotion", "browser", "ffmpeg", "ffprobe"))
def test_each_current_tool_version_change_is_toolchain_changed(tmp_path: Path, tool: str):
    root=_root(tmp_path); evidence=json.loads(_evidence(root).read_text()); evidence["tool_versions"][tool] = "changed"; _evidence(root).write_text(json.dumps(evidence))
    assert _verifier(root).verify(True)["reason_code"] == "TOOLCHAIN_CHANGED"

@pytest.mark.parametrize("receipt_case", ("missing", "directory", "empty", "not-pass", "wrong-task", "wrong-run", "wrong-hash"))
def test_receipt_read_or_binding_failure_is_safe_manifest_invalid(tmp_path: Path, receipt_case: str):
    root=_root(tmp_path); receipt=root / "docs/workmates/receipts/M09-INFRA-REAL-006-V.md"
    if receipt_case == "missing": receipt.unlink()
    elif receipt_case == "directory": receipt.unlink(); receipt.mkdir()
    elif receipt_case == "empty": receipt.write_text("")
    elif receipt_case == "not-pass": receipt.write_text("结论：**NOT PASS**")
    elif receipt_case == "wrong-task": receipt.write_text(receipt.read_text().replace("p6-real-smoke-51657b64d6d3", "other"))
    elif receipt_case == "wrong-run": receipt.write_text(receipt.read_text().replace("run-p6-51657b64d6d3", "other"))
    else: receipt.write_text(receipt.read_text().replace("18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a", "f" * 64))
    result=_verifier(root).verify(True)
    assert result["supported"] is False and result["reason_code"] == "MANIFEST_INVALID"
