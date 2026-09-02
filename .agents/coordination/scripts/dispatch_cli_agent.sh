#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: dispatch_cli_agent.sh PROJECT_ROOT ROLE TASK_ID TASK_PATH CONTRACT_COMMIT [CYCLE] [ATTEMPT]}"
role="${2:?missing role}"
task_id="${3:?missing task id}"
task_path="${4:?missing task path}"
contract_commit="${5:?missing contract commit}"
cycle="${6:-初次}"
attempt="${7:-1}"

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
for key in ("transport", "thread", "worktree", "model", "reasoning_effort"):
    print(agent.get(key, ""))
PY
)

if [[ "${registration[0]}" != "codex_cli" && "${registration[0]}" != "codex_exec" ]] || \
   [[ -z "${registration[2]}" ]] || \
   [[ "${registration[0]}" == "codex_cli" && -z "${registration[1]}" ]]; then
  printf '{"state":"not-configured","role":"%s"}\n' "$role" >"$runtime/dispatch-${role}.json"
  exit 1
fi

git -C "$project_root" cat-file -e "$contract_commit:$task_path"
[[ "$(git -C "${registration[2]}" branch --show-current)" ]] || { printf 'worker worktree has no branch\n' >&2; exit 1; }

role_lower="${role,,}"
unit="cs-board-agent-${role_lower}.service"
if "$systemctl_bin" --user is-active --quiet "$unit"; then
  current_task="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("task_id", ""))' "$runtime/${role}.json" 2>/dev/null || true)"
  [[ "$current_task" == "$task_id" ]] || { printf 'role already running another task\n' >&2; exit 1; }
  printf '{"state":"already-running","role":"%s","task_id":"%s","unit":"%s"}\n' \
    "$role" "$task_id" "$unit" >"$runtime/dispatch-${role}.json"
  exit 0
fi

runner="$project_root/.agents/coordination/scripts/run_worker_agent.sh"
"$systemd_run_bin" --user --unit="$unit" --collect --property=Type=exec \
  --working-directory="${registration[2]}" \
  --setenv=PATH=/home/ubuntu/.local/share/mise/installs/node/24/bin:/usr/local/bin:/usr/bin:/bin \
  "$runner" "$project_root" "$role" "$task_id" "$task_path" "$contract_commit" \
  "${registration[0]}" "${registration[1]}" "${registration[2]}" \
  "${registration[3]:-gpt-5.6-terra}" "${registration[4]:-medium}" "$cycle" "$attempt"

# systemd accepted and activated the real wrapper; dispatcher never writes working itself.
"$systemctl_bin" --user is-active --quiet "$unit"
printf '{"state":"started","role":"%s","task_id":"%s","unit":"%s"}\n' \
  "$role" "$task_id" "$unit" >"$runtime/dispatch-${role}.json"
