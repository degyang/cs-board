#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: run_worker_agent.sh PROJECT_ROOT ROLE TASK_ID TASK_PATH CONTRACT_COMMIT TRANSPORT THREAD WORKTREE MODEL EFFORT CYCLE ATTEMPT}"
role="${2:?missing role}"
task_id="${3:?missing task id}"
task_path="${4:?missing task path}"
contract_commit="${5:?missing contract commit}"
transport="${6:?missing transport}"
thread="${7:-}"
worktree="${8:?missing worktree}"
model="${9:-gpt-5.6-terra}"
effort="${10:-medium}"
cycle="${11:-初次}"
attempt="${12:-1}"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
node_bin="${NODE_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/node}"
codex_bin="${CODEX_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/codex}"
systemctl_bin="${SYSTEMCTL_BIN:-systemctl}"
teamctl="$dashboard_dir/teamctl.mjs"
result=1

finish() {
  local state=blocked
  [[ "$result" -eq 0 ]] && state=review
  "$node_bin" "$teamctl" agent --project "$project_root" --role "$role" \
    --state "$state" --task "$task_id" --cycle "$cycle" --attempt "$attempt" >/dev/null 2>&1 || true
  # A successful handoff must wake the short coordinator cycle immediately.
  # The periodic timer remains a recovery path if this best-effort wakeup fails.
  if [[ "$result" -eq 0 ]]; then
    "$systemctl_bin" --user start --no-block cs-board-pm.service >/dev/null 2>&1 || true
  fi
}
trap finish EXIT

# This supervised wrapper is the first component allowed to publish working.
"$node_bin" "$teamctl" agent --project "$project_root" --role "$role" \
  --state working --task "$task_id" --cycle "$cycle" --attempt "$attempt" --lease-seconds 600 >/dev/null

prompt="Use pos-agent-worker. Execute only $task_id from committed contract $task_path at coordination commit $contract_commit. Work only in $worktree on its registered branch. Run every contract gate to normal exit, write and push the required report, notify PM, then stop. Do not run team dashboard or teamctl commands: this supervised wrapper exclusively owns $role runtime and its lease. Do not approve, merge, select another task, or upgrade model/reasoning."
command=("$codex_bin" exec --dangerously-bypass-approvals-and-sandbox --model "$model" -c "model_reasoning_effort=$effort" -C "$worktree")
if [[ "$transport" == codex_cli ]]; then
  [[ -n "$thread" ]] || exit 2
  command+=(resume "$thread" "$prompt")
elif [[ "$transport" == codex_exec ]]; then
  command+=("$prompt")
else
  exit 2
fi

if "${command[@]}"; then
  result=0
fi
exit "$result"
