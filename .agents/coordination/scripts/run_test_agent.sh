#!/usr/bin/env bash
set -euo pipefail
project_root="$1"; task_id="$2"; owner="$3"; tester="$4"; contract="$5"; delivery="$6"; owner_worktree="$7"; model="$8"; effort="$9"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
node_bin="${NODE_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/node}"; codex_bin="${CODEX_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/codex}"; teamctl="$dashboard_dir/teamctl.mjs"
completion="$project_root/.agents/coordination/runtime/test-completed-$task_id.json"; result=1
finish(){ local state=blocked; [[ "$result" -eq 0 ]] && state=idle; "$node_bin" "$teamctl" agent --project "$project_root" --role "$tester" --state "$state" --task "$task_id" >/dev/null 2>&1 || true; [[ "$result" -eq 0 ]] && systemctl --user start --no-block cs-board-pm.service >/dev/null 2>&1 || true; }; trap finish EXIT
"$node_bin" "$teamctl" agent --project "$project_root" --role "$tester" --state working --task "$task_id" --cycle 验证 --attempt 1 --lease-seconds 600 >/dev/null
prompt="Act only as $tester. Validate $task_id from $contract against delivery $delivery in $owner_worktree. Run the contract gates to normal exit and write docs/agents/tests/$task_id.md with PASS, FAIL, or BLOCKED and exact evidence. Do not modify implementation, approve the task, create work, dispatch agents, or change dashboard runtime. Commit and push the test report, then stop."
if "$codex_bin" exec --dangerously-bypass-approvals-and-sandbox --model "$model" -c "model_reasoning_effort=$effort" -C "$project_root" "$prompt"; then
  mkdir -p "$(dirname "$completion")"; printf '{"task_id":"%s","delivery":"%s","result":"RECORDED","state":"completed"}\n' "$task_id" "$delivery" >"$completion"; result=0
fi
