#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: run_pm_if_needed.sh PROJECT_ROOT}"
runtime="$project_root/.agents/coordination/runtime"
probe="$project_root/.agents/coordination/scripts/pm_event_probe.py"
mkdir -p "$runtime"

exec 9>"$runtime/pm-scheduler.lock"
flock -n 9 || exit 0

event_json="$(python3 "$probe" probe --project "$project_root")"
[[ -n "$event_json" ]] || exit 0

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

prompt="Use pos-magents as the independent CEO/PM. Read docs/agents/status.md and the tracked contracts. Process exactly one short coordination cycle for this event. Prioritize stale active-work recovery over new dispatch, never overlap work for one owner, and commit only when tracked state changes. To start a codex_cli Worker, call .agents/coordination/scripts/dispatch_cli_agent.sh only after committing its DISPATCHED state; never run codex exec resume synchronously from the CEO cycle. Stop without waiting for Worker gates. Event: $event_json"
if codex exec resume --dangerously-bypass-approvals-and-sandbox "${registration[1]}" "$prompt" >>"$runtime/pm-scheduler.log" 2>&1; then
  signature="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["signature"])' <<<"$event_json")"
  python3 "$probe" ack --project "$project_root" --signature "$signature"
  printf '{"state":"completed","signature":"%s"}\n' "$signature" >"$runtime/pm-scheduler.json"
else
  printf '{"state":"failed","reason":"codex exec resume failed"}\n' >"$runtime/pm-scheduler.json"
  exit 1
fi
