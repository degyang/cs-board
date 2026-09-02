#!/usr/bin/env python3
"""Detect PM work without invoking a model.

The probe writes no tracked files. A scheduler may call ``probe`` freely; it
prints one JSON event only when the actionable signature differs from the last
successful ``ack``.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path


ROW = re.compile(r"^\|\s*`?([^|`]+)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
DEPENDENCY = re.compile(r"`([^`=]+)=APPROVED`")


def read_tasks(root: Path) -> dict[str, dict[str, str]]:
    tasks: dict[str, dict[str, str]] = {}
    for line in (root / "docs/agents/status.md").read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match or match.group(1).strip() in {"Task", "---"}:
            continue
        task_id, owner, status = (value.strip() for value in match.groups())
        tasks[task_id] = {"task_id": task_id, "owner": owner, "status": status}
    return tasks


ACTIVE_STATUSES = {"DISPATCHED", "IN_PROGRESS", "REVIEW_READY", "BLOCKED"}
ACTION_ORDER = {"recover-stale": 0, "review": 1, "promote-ready": 2, "dispatch": 3}


def parse_instant(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def recovery_reason(root: Path, task: dict[str, str], now: datetime, lease_seconds: int) -> str | None:
    runtime_path = root / ".agents/coordination/runtime" / f"{task['owner']}.json"
    try:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "runtime_missing"
    except json.JSONDecodeError:
        return "runtime_invalid"

    state = runtime.get("state")
    if state in {"idle", "blocked"}:
        return f"runtime_{state}"
    heartbeat = parse_instant(runtime.get("heartbeat_at"))
    if heartbeat is None:
        return "heartbeat_missing"
    if (now - heartbeat).total_seconds() > lease_seconds:
        return "heartbeat_expired"
    if runtime.get("task_id") != task["task_id"]:
        return "task_mismatch"
    return None


def actionable(root: Path, now: datetime | None = None, lease_seconds: int = 600) -> list[dict[str, object]]:
    tasks = read_tasks(root)
    current_time = now or datetime.now(timezone.utc)
    busy_owners = {task["owner"] for task in tasks.values() if task["status"] in ACTIVE_STATUSES}
    actions: list[dict[str, object]] = []
    for task in tasks.values():
        if task["status"] == "IN_PROGRESS":
            reason = recovery_reason(root, task, current_time, lease_seconds)
            if reason:
                actions.append({"kind": "recover-stale", "reason": reason, **task})
        elif task["status"] == "REVIEW_READY":
            actions.append({"kind": "review", **task})
        elif task["status"] == "READY" and task["owner"] not in busy_owners:
            actions.append({"kind": "dispatch", **task})
        elif task["status"] == "BACKLOG":
            contract = root / "docs/agents/tasks" / f"{task['task_id']}.md"
            if not contract.exists():
                continue
            dependencies = DEPENDENCY.findall(contract.read_text(encoding="utf-8"))
            if dependencies and all(tasks.get(item, {}).get("status") == "APPROVED" for item in dependencies):
                actions.append({"kind": "promote-ready", "dependencies": dependencies, **task})
    return sorted(actions, key=lambda item: (ACTION_ORDER[str(item["kind"])], str(item["task_id"])))


def signature(actions: list[dict[str, object]]) -> str:
    payload = json.dumps(actions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("probe", "ack"))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--signature")
    parser.add_argument("--now", help="ISO-8601 clock override for deterministic tests")
    parser.add_argument("--worker-lease-seconds", type=int, default=600)
    args = parser.parse_args()
    root = args.project.resolve()
    runtime = root / ".agents/coordination/runtime"
    state_path = runtime / "pm-event-state.json"
    runtime.mkdir(parents=True, exist_ok=True)

    if args.command == "ack":
        if not args.signature:
            parser.error("ack requires --signature")
        state_path.write_text(json.dumps({"acked_signature": args.signature}, indent=2) + "\n", encoding="utf-8")
        return 0

    now = parse_instant(args.now) if args.now else None
    if args.now and now is None:
        parser.error("--now must be an ISO-8601 timestamp")
    actions = actionable(root, now=now, lease_seconds=args.worker_lease_seconds)
    if not actions:
        return 0
    current = signature(actions)
    try:
        acknowledged = json.loads(state_path.read_text(encoding="utf-8")).get("acked_signature")
    except (FileNotFoundError, json.JSONDecodeError):
        acknowledged = None
    if current != acknowledged:
        print(json.dumps({"signature": current, "actions": actions}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
