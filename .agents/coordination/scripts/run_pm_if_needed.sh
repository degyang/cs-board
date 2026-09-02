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
worker_dispatch="$project_root/.agents/coordination/scripts/dispatch_tracked_worker.sh"
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
event_kind="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["actions"][0]["kind"])' <<<"$event_json")"

"$node_bin" "$teamctl" agent --project "$project_root" \
  --role PM --state working --task "$pm_task" \
  --cycle 调度 --attempt 1 --lease-seconds 180 >/dev/null

if [[ "$event_kind" == "record-test-ready" || "$event_kind" == "record-test-result" || "$event_kind" == "recover-delivery" || "$event_kind" == "recover-dispatch" ]]; then
  transition=(python3 "$project_root/.agents/coordination/scripts/apply_pm_transition.py" --project "$project_root" --kind "$event_kind" --task "$pm_task")
  if [[ "$event_kind" == "recover-delivery" ]]; then
    delivery="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["actions"][0]["delivery"])' <<<"$event_json")"
    transition+=(--delivery "$delivery")
  fi
  "${transition[@]}"
  git -C "$project_root" add docs/agents/status.md "docs/agents/tasks/$pm_task.md"
  git -C "$project_root" commit -m "docs(agents): $event_kind $pm_task"
  git -C "$project_root" push origin integration/mountain-v2
  signature="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["signature"])' <<<"$event_json")"
  python3 "$probe" ack --project "$project_root" --signature "$signature"
  pm_result=0
  "$worker_dispatch" "$project_root" || true
  [[ ! -x "$test_dispatch" ]] || "$test_dispatch" "$project_root" || true
  exit 0
fi

readarray -t registration < <(python3 - "$project_root/.agents/coordination/agents.json" <<'PY'
import json, sys
pm = json.load(open(sys.argv[1], encoding="utf-8"))["agents"]["PM"]
print(pm.get("transport", ""))
print(pm.get("thread", ""))
PY
)

if [[ "${registration[0]}" != "codex_exec" ]]; then
  printf '{"state":"not-configured","reason":"PM is not registered for bounded codex_exec"}\n' >"$runtime/pm-scheduler.json"
  exit 0
fi

prompt="Act only as the bounded PM for this single event. Read only docs/agents/agreements.md, docs/agents/milestone-m1-manual-skills-closure.md, docs/agents/status.md, and the event task contract/report needed for the decision; do not inspect every worktree, load historical reviews, run tests, or perform a general preflight. Create/decompose tasks, dispatch Workers, verify Tester report completeness, decide APPROVED/CHANGES_REQUESTED/BLOCKED, and decide whether the stage goal requires a next task. Do not act as CEO or Tester. record-test-ready changes a verified Worker handoff to TEST_READY only. record-test-result changes a bound Tester result to PM_DECISION only. pm-review reads the Tester report and records the final decision plus next-task decision. Never dispatch later work for an owner with WORKING, TEST_READY, TESTING, or PM_DECISION work. Make the smallest tracked edit, commit and push, then exit immediately. Event: $event_json"
prompt="$prompt Model governance: default every new task to a moderate model and reasoning effort. Only after three failed rework attempts may the CEO propose escalation. Never assign gpt-5.6-sol with high, xhigh, max, or ultra unless docs/agents/agreements.md records explicit user approval for that exact task and level."
prompt="$prompt Tester execution is owned exclusively by dispatch_test_agent.sh and its supervised service. Tester provides evidence but never a verdict."
prompt="$prompt A resolve-blocker event requires a concrete bounded diagnosis/recovery task or an explicit external dependency record; do not merely repeat that the task is blocked."
prompt="$prompt Treat blocker_facts as verified scheduler evidence. Never append or commit the same blocker decision when those facts have not changed. A recover-delivery or recover-dispatch event is handled deterministically before this model turn."
prompt="$prompt Worker execution is owned exclusively by dispatch_cli_agent.sh and run_worker_agent.sh. Never create an orchestrator Worker or write working runtime yourself. After committing DISPATCHED, invoke the dispatcher asynchronously; only its supervised wrapper may publish working, review, or blocked."
prompt="$prompt A retire-agent action is executable policy: recheck that the non-protected owner has only terminal tasks, no active service/lease, and exceeded the reported retention. Then remove only its current registry entry and transient runtime, preserve all history, commit and push. Under capacity pressure process the oldest timed-out candidate first."

if timeout --signal=TERM --kill-after=5s 90s \
  "$codex_bin" exec --dangerously-bypass-approvals-and-sandbox --model gpt-5.6-terra \
  -c model_reasoning_effort=medium -C "$project_root" "$prompt" >>"$runtime/pm-scheduler.log" 2>&1; then
  signature="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["signature"])' <<<"$event_json")"
  remaining="$(python3 "$probe" probe --project "$project_root" --max-actions 1)"
  remaining_signature="$(python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data)["signature"] if data else "")' <<<"$remaining")"
  if [[ "$remaining_signature" == "$signature" ]]; then
    if [[ "$event_kind" == "resolve-blocker" ]]; then
      python3 "$probe" ack --project "$project_root" --signature "$signature"
      printf '{"state":"stable-blocker","signature":"%s","reason":"facts acknowledged; wait for evidence change"}\n' "$signature" >"$runtime/pm-scheduler.json"
      pm_result=0
      exit 0
    fi
    printf '{"state":"incomplete","signature":"%s","reason":"actionable state unchanged"}\n' "$signature" >"$runtime/pm-scheduler.json"
    exit 1
  fi
  python3 "$probe" ack --project "$project_root" --signature "$signature"
  printf '{"state":"completed","signature":"%s"}\n' "$signature" >"$runtime/pm-scheduler.json"
  pm_result=0
  "$worker_dispatch" "$project_root" || true
  [[ ! -x "$test_dispatch" ]] || "$test_dispatch" "$project_root" || true
else
  signature="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["signature"])' <<<"$event_json")"
  remaining="$(python3 "$probe" probe --project "$project_root" --max-actions 1)"
  remaining_signature="$(python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data)["signature"] if data else "")' <<<"$remaining")"
  if [[ "$remaining_signature" != "$signature" ]]; then
    git -C "$project_root" push origin integration/mountain-v2
    python3 "$probe" ack --project "$project_root" --signature "$signature"
    printf '{"state":"completed-after-timeout","signature":"%s"}\n' "$signature" >"$runtime/pm-scheduler.json"
    pm_result=0
    "$worker_dispatch" "$project_root" || true
    exit 0
  fi
  printf '{"state":"failed","reason":"PM process failed without a tracked transition"}\n' >"$runtime/pm-scheduler.json"
  exit 1
fi
