#!/usr/bin/env python3
"""Short, deterministic CEO audit of goal alignment, bottlenecks and PM progress."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROW = re.compile(r"^\|\s*`?([^|`]+)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
OPEN = {"READY", "DISPATCHED", "IN_PROGRESS", "WORKING", "TEST_READY", "TESTING", "PM_DECISION", "CHANGES_REQUESTED", "BLOCKED", "ARBITRATION"}
DISPUTED = {"CHANGES_REQUESTED", "BLOCKED"}
FAILED_PM_STATES = {"failed", "incomplete"}


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def update_arbitration_state(runtime: Path, tasks: list[dict[str, str]], threshold: int) -> dict[str, dict[str, object]]:
    path = runtime / "arbitration-state.json"
    previous = read_json(path).get("tasks", {})
    state = previous if isinstance(previous, dict) else {}
    for task in tasks:
        task_id = task["task_id"]
        entry = state.get(task_id, {})
        entry = entry if isinstance(entry, dict) else {}
        last_status = entry.get("last_status")
        count = int(entry.get("dispute_entries", 0))
        if task["status"] in DISPUTED and last_status != task["status"]:
            count += 1
        state[task_id] = {
            "last_status": task["status"],
            "dispute_entries": count,
            "threshold": threshold,
        }
    runtime.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tasks": state}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return state


def audit(root: Path) -> dict[str, object]:
    text = (root / "docs/agents/status.md").read_text(encoding="utf-8")
    goal = (root / "docs/agents/milestone-m1-manual-skills-closure.md").read_text(encoding="utf-8")
    tasks = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match and match.group(1).strip() not in {"Task", "---"}:
            tasks.append(dict(zip(("task_id", "owner", "status"), map(str.strip, match.groups()))))
    alerts: list[dict[str, object]] = []
    active = [task for task in tasks if task["status"] in OPEN]
    runtime = root / ".agents/coordination/runtime"
    policy = read_json(root / ".agents/coordination/policy.json")
    arbitration_threshold = max(3, int(policy.get("arbitration_after_dispute_entries", 3)))
    arbitration = update_arbitration_state(runtime, tasks, arbitration_threshold)
    for task in active:
        dispute_entries = int(arbitration.get(task["task_id"], {}).get("dispute_entries", 0))
        if task["status"] == "ARBITRATION":
            alerts.append({"kind": "human-arbitration", "task_id": task["task_id"], "message": "task is in 冲裁 and awaits explicit human direction"})
            continue
        if task["status"] in DISPUTED and dispute_entries >= arbitration_threshold:
            alerts.append({"kind": "arbitration-required", "task_id": task["task_id"], "dispute_entries": dispute_entries, "message": "task entered a disputed state three times; move it to 冲裁"})
        if task["status"] == "BLOCKED":
            alerts.append({"kind": "blocked", "task_id": task["task_id"], "message": "blocked task requires PM resolution plan"})
        if task["task_id"] not in goal and task["task_id"] not in {"CEO-RECOVERY-002"}:
            alerts.append({"kind": "goal-drift", "task_id": task["task_id"], "message": "active PM work is not named in the stage-goal contract"})
    for suffix in ("WEB", "CORE", "MEDIA"):
        owner = f"WORKER_{suffix}"
        if any(task["owner"] == owner and task["status"] == "READY" for task in active) and not any(
            task["owner"] == owner and task["status"] in OPEN - {"READY"} for task in active
        ):
            alerts.append({"kind": "idle-capacity", "owner": owner, "message": "ready work and idle capacity coexist"})

    progress_path = runtime / "ceo-progress-state.json"
    scheduler = read_json(runtime / "pm-scheduler.json")
    material = json.dumps(
        [{"kind": item["kind"], "task_id": item.get("task_id"), "owner": item.get("owner")} for item in alerts],
        sort_keys=True,
        separators=(",", ":"),
    )
    progress_signature = hashlib.sha256(material.encode()).hexdigest() if alerts else ""
    previous = read_json(progress_path)
    unchanged_cycles = (
        int(previous.get("unchanged_cycles", 0)) + 1
        if progress_signature and previous.get("signature") == progress_signature
        else (1 if progress_signature else 0)
    )
    runtime.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps({"signature": progress_signature, "unchanged_cycles": unchanged_cycles}, indent=2) + "\n",
        encoding="utf-8",
    )
    if unchanged_cycles >= 2 and scheduler.get("state") in FAILED_PM_STATES:
        alerts.append({
            "kind": "pm-stalled",
            "cycles": unchanged_cycles,
            "scheduler_state": scheduler.get("state"),
            "message": "PM failed to change the same actionable project state for two CEO cycles",
        })
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "goal": "M1-MANUAL-SKILLS",
        "progress_signature": progress_signature,
        "unchanged_cycles": unchanged_cycles,
        "alerts": alerts,
        "needs_pm": any(item["kind"] != "human-arbitration" for item in alerts),
        "needs_human": any(item["kind"] == "human-arbitration" for item in alerts),
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path(sys.argv[1]).resolve()), ensure_ascii=False))
