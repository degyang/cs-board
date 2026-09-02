#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: run_pm_if_needed.sh PROJECT_ROOT}"
runtime="$project_root/.agents/coordination/runtime"
probe="$project_root/.agents/coordination/scripts/pm_event_probe.py"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
node_bin="${NODE_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/node}"
codex_bin="${CODEX_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/codex}"
teamctl="$dashboard_dir/teamctl.mjs"
review_dispatch="$project_root/.agents/coordination/scripts/dispatch_review_agent.sh"
pm_task=""
mkdir -p "$runtime"

mark_pm_idle() {
  [[ -n "$pm_task" ]] || return 0
  "$node_bin" "$teamctl" agent --project "$project_root" \
    --role PM --state idle >/dev/null 2>&1 || true
}

trap mark_pm_idle EXIT

exec 9>"$runtime/pm-scheduler.lock"
flock -n 9 || exit 0

# Review dispatch is deterministic and asynchronous; it must not depend on a PM model turn.
[[ ! -x "$review_dispatch" ]] || "$review_dispatch" "$project_root" || true

event_json="$(python3 "$probe" probe --project "$project_root" --max-actions 1)"
[[ -n "$event_json" ]] || exit 0
pm_task="$(python3 -c 'import json,sys; event=json.load(sys.stdin); print(event["actions"][0].get("task_id", "COORDINATION"))' <<<"$event_json")"

"$node_bin" "$teamctl" agent --project "$project_root" \
  --role PM --state working --task "$pm_task" \
  --cycle 调度 --attempt 1 --lease-seconds 180 >/dev/null

readarray -t registration < <(python3 - "$project_root/.agents/coordination/agents.json" <<'PY'
import json, sys
pm = json.load(open(sys.argv[1], encoding="utf-8"))["agents"]["PM"]
print(pm.get("transport", ""))
print(pm.get("thread", ""))
PY
)

if [[ "${registration[0]}" != "codex_cli" || -z "${registration[1]}" ]]; then
  printf '{"state":"not-configured","reason":"PM is not a registered codex_cli session"}\n' >"$runtime/pm-scheduler.json"
  exit 0
fi

prompt="Use pos-magents as the independent CEO/PM. First read docs/agents/agreements.md: its newest ACTIVE timeline entry is the governing working agreement and historical entries must remain append-only. Then read docs/agents/status.md and the tracked contracts. Process exactly one short coordination cycle for this event. A record-review-ready action means the Worker has handed off to review: verify its committed report/delivery reference, then update tracked status to REVIEW_READY without running long gates. A dispatch action whose status is CHANGES_REQUESTED means re-dispatch that same bounded correction before any later task for its owner. Prioritize stale active-work recovery and corrections over new dispatch, never overlap work for one owner, and commit only when tracked state changes. To start a codex_cli Worker, call .agents/coordination/scripts/dispatch_cli_agent.sh only after committing its DISPATCHED state; never run codex exec resume synchronously from the CEO cycle. Stop without waiting for Worker gates. Event: $event_json"
prompt="$prompt Model governance: default every new task to a moderate model and reasoning effort. Only after three failed rework attempts may the CEO propose escalation. Never assign gpt-5.6-sol with high, xhigh, max, or ultra unless docs/agents/agreements.md records explicit user approval for that exact task and level."
prompt="$prompt Reviewer execution is owned exclusively by dispatch_review_agent.sh and its supervised systemd service. Do not register, spawn, or pre-mark an orchestrator Reviewer; only consume a completed review verdict and update tracked state."
prompt="$prompt Worker execution is owned exclusively by dispatch_cli_agent.sh and run_worker_agent.sh. Never create an orchestrator Worker or write working runtime yourself. After committing DISPATCHED, invoke the dispatcher asynchronously; only its supervised wrapper may publish working, review, or blocked."

if timeout --signal=TERM --kill-after=5s 60s \
  "$codex_bin" exec resume --dangerously-bypass-approvals-and-sandbox "${registration[1]}" "$prompt" >>"$runtime/pm-scheduler.log" 2>&1; then
  signature="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["signature"])' <<<"$event_json")"
  remaining="$(python3 "$probe" probe --project "$project_root" --max-actions 1)"
  remaining_signature="$(python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data)["signature"] if data else "")' <<<"$remaining")"
  if [[ "$remaining_signature" == "$signature" ]]; then
    printf '{"state":"incomplete","signature":"%s","reason":"actionable state unchanged"}\n' "$signature" >"$runtime/pm-scheduler.json"
    exit 1
  fi
  python3 "$probe" ack --project "$project_root" --signature "$signature"
  printf '{"state":"completed","signature":"%s"}\n' "$signature" >"$runtime/pm-scheduler.json"
else
  printf '{"state":"failed","reason":"codex exec resume failed"}\n' >"$runtime/pm-scheduler.json"
  exit 1
fi
