#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: run_review_agent.sh PROJECT_ROOT TASK_ID CONTRACT DELIVERY OWNER_WORKTREE}"
task_id="${2:?missing task id}"
contract="${3:?missing contract}"
delivery="${4:?missing delivery}"
owner_worktree="${5:?missing owner worktree}"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
node_bin="${NODE_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/node}"
codex_bin="${CODEX_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/codex}"
teamctl="$dashboard_dir/teamctl.mjs"
result=1

finish() {
  local state=blocked
  [[ "$result" -eq 0 ]] && state=review
  "$node_bin" "$teamctl" agent --project "$project_root" --role REVIEWER \
    --state "$state" --task "$task_id" --cycle 审核 --attempt 1 >/dev/null 2>&1 || true
}
trap finish EXIT

# The wrapper is the real supervised Reviewer process. Only it may publish working.
"$node_bin" "$teamctl" agent --project "$project_root" --role REVIEWER \
  --state working --task "$task_id" --cycle 审核 --attempt 1 --lease-seconds 600 >/dev/null

prompt="Use pos-agent-reviewer. Independently review $task_id from $contract against delivery $delivery in owner worktree $owner_worktree. The coordination root is $project_root. Reproduce risk-proportionate gates, write and push docs/agents/reviews/$task_id.md, notify PM, then stop. Do not modify Worker implementation, approve a merge, or select another task. Do not upgrade model or reasoning effort."
if "$codex_bin" exec --dangerously-bypass-approvals-and-sandbox --model gpt-5.6-terra \
  -c model_reasoning_effort=medium -C "$project_root" "$prompt"; then
  result=0
fi
exit "$result"
