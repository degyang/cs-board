#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: dispatch_cli_agent.sh PROJECT_ROOT ROLE TASK_ID TASK_PATH CONTRACT_COMMIT}"
role="${2:?missing role}"
task_id="${3:?missing task id}"
task_path="${4:?missing task path}"
contract_commit="${5:?missing contract commit}"

[[ "$role" =~ ^[A-Z][A-Z0-9_-]*$ ]] || { printf 'invalid role\n' >&2; exit 2; }
[[ "$task_id" =~ ^[A-Z0-9][A-Z0-9_-]*$ ]] || { printf 'invalid task id\n' >&2; exit 2; }

runtime="$project_root/.agents/coordination/runtime"
registry="$project_root/.agents/coordination/agents.json"
systemctl_bin="${SYSTEMCTL_BIN:-systemctl}"
systemd_run_bin="${SYSTEMD_RUN_BIN:-systemd-run}"
npm_bin="${NPM_BIN:-npm}"
codex_bin="${CODEX_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/codex}"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
mkdir -p "$runtime"

exec 8>"$runtime/dispatch-${role}.lock"
flock -n 8 || exit 0

readarray -t registration < <(python3 - "$registry" "$role" <<'PY'
import json, sys
agent = json.load(open(sys.argv[1], encoding="utf-8"))["agents"][sys.argv[2]]
for key in ("transport", "thread", "worktree", "model"):
    print(agent.get(key, ""))
PY
)

if [[ "${registration[0]}" != "codex_cli" || -z "${registration[1]}" || -z "${registration[2]}" ]]; then
  printf '{"state":"not-configured","role":"%s"}\n' "$role" >"$runtime/dispatch-${role}.json"
  exit 1
fi

git -C "$project_root" cat-file -e "$contract_commit:$task_path"
[[ "$(git -C "${registration[2]}" branch --show-current)" ]] || { printf 'worker worktree has no branch\n' >&2; exit 1; }

role_lower="${role,,}"
unit="cs-board-agent-${role_lower}.service"
if "$systemctl_bin" --user is-active --quiet "$unit"; then
  printf '{"state":"already-running","role":"%s","task_id":"%s"}\n' "$role" "$task_id" >"$runtime/dispatch-${role}.json"
  exit 0
fi

prompt="Use the pos-agent-worker skill. Execute only $task_id from committed contract $task_path at coordination commit $contract_commit. Work only in your registered worktree and branch. Run every contract gate to normal exit, write and push the required report, notify the registered PM, then stop. Do not approve, merge, or select another task."

"$systemd_run_bin" --user --unit="$unit" --collect --property=Type=exec \
  --working-directory="${registration[2]}" \
  --setenv=PATH=/home/ubuntu/.local/share/mise/installs/node/24/bin:/usr/local/bin:/usr/bin:/bin \
  "$codex_bin" exec resume --dangerously-bypass-approvals-and-sandbox \
  --model "${registration[3]:-gpt-5.6-terra}" "${registration[1]}" "$prompt"

"$npm_bin" --prefix "$dashboard_dir" run agent -- \
  --project "$project_root" --role "$role" --state working --task "$task_id" \
  --cycle 返工 --attempt 1 --lease-seconds 600 >/dev/null
printf '{"state":"started","role":"%s","task_id":"%s","unit":"%s"}\n' \
  "$role" "$task_id" "$unit" >"$runtime/dispatch-${role}.json"
