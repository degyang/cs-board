#!/usr/bin/env python3
"""Machine-checkable release gates for the project-local tmux team."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Result:
    state: str
    reason: str
    details: list[dict[str, Any]]

    @property
    def ready(self) -> bool:
        return self.state in {"READY_FOR_REFRESH", "READY_FOR_BROWSER", "COMPLETE"}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest root must be an object")
    return value


def _project_path(project: Path, raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else project / path


def _receipt_result(project: Path, item: dict[str, Any]) -> dict[str, Any]:
    path = _project_path(project, item["path"])
    detail: dict[str, Any] = {"path": str(path), "state": "PASS"}
    if not path.is_file():
        return {**detail, "state": "MISSING", "reason": "evidence file does not exist"}

    text = path.read_text(encoding="utf-8", errors="replace")
    fail_regex = item.get("fail_regex")
    if fail_regex and re.search(fail_regex, text):
        return {**detail, "state": "BLOCKED", "reason": "failure marker matched"}
    pass_regex = item.get("pass_regex")
    if pass_regex and not re.search(pass_regex, text):
        return {**detail, "state": "INVALID", "reason": "required pass marker missing"}

    evidence_mtime = path.stat().st_mtime_ns
    stale_against: list[str] = []
    for dependency in item.get("newer_than", []):
        dependency_path = _project_path(project, dependency)
        if not dependency_path.is_file():
            return {
                **detail,
                "state": "MISSING_DEPENDENCY",
                "reason": f"dependency missing: {dependency_path}",
            }
        if evidence_mtime <= dependency_path.stat().st_mtime_ns:
            stale_against.append(str(dependency_path))
    if stale_against:
        return {
            **detail,
            "state": "STALE",
            "reason": "evidence is not newer than its implementation input",
            "stale_against": stale_against,
        }
    detail["mtime_ns"] = evidence_mtime
    return detail


def _json_value(payload: Any, dotted_path: str) -> Any:
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(dotted_path)
    return current


def _runtime_result(item: dict[str, Any]) -> dict[str, Any]:
    url = item["url"]
    detail: dict[str, Any] = {"url": url, "state": "PASS"}
    try:
        with urllib.request.urlopen(url, timeout=float(item.get("timeout_seconds", 3))) as response:
            body = response.read()
            detail.update(
                status=response.status,
                bytes=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
            )
            expected_status = int(item.get("status", 200))
            if response.status != expected_status:
                return {**detail, "state": "BLOCKED", "reason": "unexpected HTTP status"}
            marker = item.get("contains")
            if marker and marker not in body.decode("utf-8", errors="replace"):
                return {**detail, "state": "BLOCKED", "reason": "served marker missing"}
            if "json_path" in item:
                value = _json_value(json.loads(body), item["json_path"])
                if not isinstance(value, list):
                    return {**detail, "state": "INVALID", "reason": "json_path is not a list"}
                detail["count"] = len(value)
                if len(value) < int(item.get("min_count", 0)):
                    return {
                        **detail,
                        "state": "EMPTY_RUNTIME_DATA",
                        "reason": f"requires at least {item['min_count']} records",
                    }
    except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
        return {**detail, "state": "BLOCKED", "reason": f"probe failed: {exc}"}
    return detail


def evaluate(manifest_path: Path, through: str | None = None) -> Result:
    manifest = _read_json(manifest_path)
    project = _project_path(manifest_path.parent, manifest.get("project_root", ".")).resolve()
    phases = manifest.get("phases", [])
    details: list[dict[str, Any]] = []
    phase_states: dict[str, str] = {}

    for phase in phases:
        phase_id = phase["id"]
        unmet = [dependency for dependency in phase.get("depends_on", []) if phase_states.get(dependency) != "PASS"]
        if unmet:
            return Result("BLOCKED_DEPENDENCY", f"{phase_id} waits for {', '.join(unmet)}", details)
        evidence = [_receipt_result(project, item) for item in phase.get("evidence", [])]
        details.append({"phase": phase_id, "evidence": evidence})
        bad = next((item for item in evidence if item["state"] != "PASS"), None)
        if bad:
            phase_states[phase_id] = bad["state"]
            return Result(bad["state"], f"{phase_id}: {bad['reason']}", details)
        phase_states[phase_id] = "PASS"
        if through == phase_id:
            state = "READY_FOR_REFRESH" if phase_id == "verification" else "PASS"
            return Result(state, f"all gates through {phase_id} passed", details)

    runtime_details = [_runtime_result(item) for item in manifest.get("runtime_checks", [])]
    details.append({"phase": "runtime", "evidence": runtime_details})
    bad_runtime = next((item for item in runtime_details if item["state"] != "PASS"), None)
    if bad_runtime:
        return Result(bad_runtime["state"], f"runtime: {bad_runtime['reason']}", details)

    browser = manifest.get("browser_acceptance")
    if browser:
        browser_detail = _receipt_result(project, browser)
        details.append({"phase": "browser", "evidence": [browser_detail]})
        if browser_detail["state"] != "PASS":
            return Result("READY_FOR_BROWSER", "runtime passed; manual browser acceptance pending", details)
    return Result("COMPLETE", "all configured release gates passed", details)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _payload(manifest: Path, result: Result) -> dict[str, Any]:
    return {
        "manifest": str(manifest.resolve()),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "state": result.state,
        "reason": result.reason,
        "details": result.details,
    }


def _broadcast(manifest: dict[str, Any], message: str) -> None:
    target = manifest.get("notify", {}).get("tmux_target")
    if target:
        subprocess.run(["tmux", "display-message", "-t", target, message], check=False)
    signal = manifest.get("notify", {}).get("tmux_signal")
    if signal:
        subprocess.run(["tmux", "wait-for", "-S", signal], check=False)


def _prompt_pm_when_idle(manifest: dict[str, Any], message: str) -> bool:
    notify = manifest.get("notify", {})
    if not notify.get("prompt_when_idle"):
        return True
    target = notify.get("tmux_target")
    if not target:
        return False
    command = subprocess.run(
        ["tmux", "display-message", "-p", "-t", target, "#{pane_current_command}"],
        check=False,
        capture_output=True,
        text=True,
    )
    pane = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", target, "-S", "-8"],
        check=False,
        capture_output=True,
        text=True,
    )
    if command.returncode != 0 or pane.returncode != 0:
        return False
    current_command = command.stdout.strip()
    codex_idle = current_command in {"node", "codex"} and "Ask Codex to do anything" in pane.stdout
    claude_idle = (
        current_command == "claude"
        and "❯" in pane.stdout
        and "esc to interrupt" not in pane.stdout
    )
    if not (codex_idle or claude_idle):
        return False
    prompt = f"Release guard event: {message}. Read the gate status JSON and act only per team-contract dependencies; never bypass a non-ready gate."
    sent = subprocess.run(["tmux", "send-keys", "-t", target, "-l", "--", prompt], check=False)
    if sent.returncode != 0:
        return False
    time.sleep(0.2)
    return subprocess.run(["tmux", "send-keys", "-t", target, "Enter"], check=False).returncode == 0


def command_check(args: argparse.Namespace) -> int:
    result = evaluate(args.manifest, args.through)
    payload = _payload(args.manifest, result)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.ready else 2


def command_watch(args: argparse.Namespace) -> int:
    manifest = _read_json(args.manifest)
    project = _project_path(args.manifest.parent, manifest.get("project_root", ".")).resolve()
    status_path = _project_path(project, manifest["status_file"])
    event_path = _project_path(project, manifest["event_log"])
    previous_signature = ""
    pending_prompt: tuple[str, str] | None = None
    while True:
        result = evaluate(args.manifest)
        payload = _payload(args.manifest, result)
        signature = json.dumps(
            {"state": result.state, "reason": result.reason, "details": result.details},
            sort_keys=True,
        )
        _atomic_json(status_path, payload)
        if signature != previous_signature:
            event_path.parent.mkdir(parents=True, exist_ok=True)
            with event_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
            message = f"release gate {manifest['gate_id']}: {result.state} — {result.reason}"
            _broadcast(manifest, message)
            pending_prompt = (signature, message)
            previous_signature = signature
        if pending_prompt and _prompt_pm_when_idle(manifest, pending_prompt[1]):
            pending_prompt = None
        if args.once:
            return 0 if result.ready else 2
        time.sleep(args.interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    check.add_argument("manifest", type=Path)
    check.add_argument("--through", choices=["implementation", "verification", "refresh"])
    check.set_defaults(function=command_check)
    watch = subparsers.add_parser("watch")
    watch.add_argument("manifest", type=Path)
    watch.add_argument("--interval", type=float, default=5.0)
    watch.add_argument("--once", action="store_true")
    watch.set_defaults(function=command_watch)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.function(args)


if __name__ == "__main__":
    sys.exit(main())
