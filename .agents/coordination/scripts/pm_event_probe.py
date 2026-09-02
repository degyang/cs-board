#!/usr/bin/env python3
"""Detect PM work without invoking a model.

The probe writes no tracked files. A scheduler may call ``probe`` freely; it
prints one JSON event only when the actionable signature differs from the last
successful ``ack``.
"""

from __future__ import annotations

import argparse
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


def actionable(root: Path) -> list[dict[str, object]]:
    tasks = read_tasks(root)
    actions: list[dict[str, object]] = []
    for task in tasks.values():
        if task["status"] == "REVIEW_READY":
            actions.append({"kind": "review", **task})
        elif task["status"] == "READY":
            actions.append({"kind": "dispatch", **task})
        elif task["status"] == "BACKLOG":
            contract = root / "docs/agents/tasks" / f"{task['task_id']}.md"
            if not contract.exists():
                continue
            dependencies = DEPENDENCY.findall(contract.read_text(encoding="utf-8"))
            if dependencies and all(tasks.get(item, {}).get("status") == "APPROVED" for item in dependencies):
                actions.append({"kind": "promote-ready", "dependencies": dependencies, **task})
    return sorted(actions, key=lambda item: (str(item["kind"]), str(item["task_id"])))


def signature(actions: list[dict[str, object]]) -> str:
    payload = json.dumps(actions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("probe", "ack"))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--signature")
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

    actions = actionable(root)
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
