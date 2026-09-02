#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: run_pm_if_needed.sh PROJECT_ROOT}"
runtime="$project_root/.agents/coordination/runtime"
probe="$project_root/.agents/coordination/scripts/pm_event_probe.py"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
node_bin="${NODE_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/node}"
codex_bin="${CODEX_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/codex}"
teamctl="$dashboard_dir/teamctl.mjs"
test_dispatch="$project_root/.agents/coordination/scripts/dispatch_test_agent.sh"
pm_task=""
pm_result=1
mkdir -p "$runtime"

mark_pm_idle() {
  [[ -n "$pm_task" ]] || return 0
  local state=blocked
  [[ "$pm_result" -eq 0 ]] && state=idle
  "$node_bin" "$teamctl" agent --project "$project_root" \
    --role PM --state "$state" --task "$pm_task" >/dev/null 2>&1 || true
}

trap mark_pm_idle EXIT

exec 9>"$runtime/pm-scheduler.lock"
flock -n 9 || exit 0

# Tester dispatch is deterministic and asynchronous; it must not depend on a PM model turn.
[[ ! -x "$test_dispatch" ]] || "$test_dispatch" "$project_root" || true

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

prompt="Use pos-magents only as PM. Read the newest ACTIVE agreement and current milestone goal, status, and contracts. Process exactly one event. You create/decompose tasks, dispatch Workers, verify Tester report completeness, decide APPROVED/CHANGES_REQUESTED/BLOCKED, and decide whether the stage goal requires a next task. You do not act as CEO, run long gates, or perform Tester work. record-test-ready changes a verified Worker handoff to TEST_READY only. record-test-result changes a bound Tester result to PM_DECISION only. pm-review reads the Tester report and records the final decision plus next-task decision. Never dispatch later work for an owner with WORKING, TEST_READY, TESTING, or PM_DECISION work. Do not run dashboard commands. Event: $event_json"
prompt="$prompt Model governance: default every new task to a moderate model and reasoning effort. Only after three failed rework attempts may the CEO propose escalation. Never assign gpt-5.6-sol with high, xhigh, max, or ultra unless docs/agents/agreements.md records explicit user approval for that exact task and level."
prompt="$prompt Tester execution is owned exclusively by dispatch_test_agent.sh and its supervised service. Tester provides evidence but never a verdict."
prompt="$prompt A resolve-blocker event requires a concrete bounded diagnosis/recovery task or an explicit external dependency record; do not merely repeat that the task is blocked."
prompt="$prompt Worker execution is owned exclusively by dispatch_cli_agent.sh and run_worker_agent.sh. Never create an orchestrator Worker or write working runtime yourself. After committing DISPATCHED, invoke the dispatcher asynchronously; only its supervised wrapper may publish working, review, or blocked."
prompt="$prompt A retire-agent action is executable policy: recheck that the non-protected owner has only terminal tasks, no active service/lease, and exceeded the reported retention. Then remove only its current registry entry and transient runtime, preserve all history, commit and push. Under capacity pressure process the oldest timed-out candidate first."

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
  pm_result=0
  [[ ! -x "$test_dispatch" ]] || "$test_dispatch" "$project_root" || true
else
  printf '{"state":"failed","reason":"codex exec resume failed"}\n' >"$runtime/pm-scheduler.json"
  exit 1
fi
