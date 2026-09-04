from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "workmates_release_guard.py"
SPEC = importlib.util.spec_from_file_location("workmates_release_guard", MODULE_PATH)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def _write(path: Path, text: str, mtime_ns: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, ns=(mtime_ns, mtime_ns))


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "gate.json"
    path.write_text(
        json.dumps(
            {
                "project_root": ".",
                "phases": [
                    {
                        "id": "implementation",
                        "evidence": [{"path": "impl.md", "pass_regex": "PASS", "fail_regex": "FAIL|BLOCKED"}],
                    },
                    {
                        "id": "verification",
                        "depends_on": ["implementation"],
                        "evidence": [
                            {
                                "path": "verify.md",
                                "pass_regex": "PASS",
                                "fail_regex": "FAIL|BLOCKED",
                                "newer_than": ["impl.md"],
                            }
                        ],
                    },
                ],
                "runtime_checks": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_missing_implementation_blocks(tmp_path: Path) -> None:
    result = guard.evaluate(_manifest(tmp_path), "verification")
    assert result.state == "MISSING"


def test_failed_receipt_blocks_even_if_it_contains_pass_elsewhere(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _write(tmp_path / "impl.md", "status PASS", 10)
    _write(tmp_path / "verify.md", "focused PASS\nstatus BLOCKED", 20)
    result = guard.evaluate(manifest, "verification")
    assert result.state == "BLOCKED"


def test_verification_older_than_implementation_is_stale(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _write(tmp_path / "verify.md", "status PASS", 10)
    _write(tmp_path / "impl.md", "status PASS", 20)
    result = guard.evaluate(manifest, "verification")
    assert result.state == "STALE"


def test_current_pass_receipts_unlock_refresh(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _write(tmp_path / "impl.md", "status PASS", 10)
    _write(tmp_path / "verify.md", "status PASS", 20)
    result = guard.evaluate(manifest, "verification")
    assert result.state == "READY_FOR_REFRESH"
    assert result.ready


def test_empty_runtime_dataset_is_explicitly_blocked(monkeypatch, tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _write(tmp_path / "impl.md", "status PASS", 10)
    _write(tmp_path / "verify.md", "status PASS", 20)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["runtime_checks"] = [{"url": "http://example.invalid", "json_path": "items", "min_count": 1}]
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"items": []}'

    monkeypatch.setattr(guard.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    result = guard.evaluate(manifest)
    assert result.state == "EMPTY_RUNTIME_DATA"


def test_pm_prompt_waits_while_agent_is_busy(monkeypatch) -> None:
    calls = []

    class Completed:
        def __init__(self, args, stdout="", returncode=0):
            self.args = args
            self.stdout = stdout
            self.returncode = returncode

    def run(args, **_kwargs):
        calls.append(args)
        if "#{pane_current_command}" in args:
            return Completed(args, "node\n")
        if "capture-pane" in args:
            return Completed(args, "Working (10s)\n")
        return Completed(args)

    monkeypatch.setattr(guard.subprocess, "run", run)
    assert not guard._prompt_pm_when_idle(
        {"notify": {"tmux_target": "session:pm", "prompt_when_idle": True}}, "changed"
    )
    assert not any("send-keys" in call for call in calls)


def test_pm_prompt_is_delivered_only_at_idle_prompt(monkeypatch) -> None:
    calls = []

    class Completed:
        def __init__(self, args, stdout="", returncode=0):
            self.args = args
            self.stdout = stdout
            self.returncode = returncode

    def run(args, **_kwargs):
        calls.append(args)
        if "#{pane_current_command}" in args:
            return Completed(args, "node\n")
        if "capture-pane" in args:
            return Completed(args, "› Ask Codex to do anything\n")
        return Completed(args)

    monkeypatch.setattr(guard.subprocess, "run", run)
    monkeypatch.setattr(guard.time, "sleep", lambda _seconds: None)
    assert guard._prompt_pm_when_idle(
        {"notify": {"tmux_target": "session:pm", "prompt_when_idle": True}}, "changed"
    )
    send_calls = [call for call in calls if "send-keys" in call]
    assert len(send_calls) == 2
    assert "Release guard event" in send_calls[0][-1]
