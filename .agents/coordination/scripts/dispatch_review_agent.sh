#!/usr/bin/env bash
set -euo pipefail

project_root="${1:?usage: dispatch_review_agent.sh PROJECT_ROOT}"
runtime="$project_root/.agents/coordination/runtime"
unit="cs-board-agent-reviewer.service"
systemctl_bin="${SYSTEMCTL_BIN:-systemctl}"
systemd_run_bin="${SYSTEMD_RUN_BIN:-systemd-run}"
mkdir -p "$runtime"

review_transport="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agents"].get("REVIEWER", {}).get("transport", ""))' "$project_root/.agents/coordination/agents.json")"
[[ "$review_transport" == "codex_exec" ]] || exit 0

exec 7>"$runtime/dispatch-REVIEWER.lock"
flock -n 7 || exit 0
if "$systemctl_bin" --user is-active --quiet "$unit"; then
  exit 0
fi

readarray -t task < <(python3 - "$project_root" <<'PY'
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1])
row = re.compile(r"^\|\s*`?([^|`]+)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*`?([^|`]+)`?\s*\|\s*`?([^|`]+)`?")
registry = json.loads((root / '.agents/coordination/agents.json').read_text())['agents']
runtime_path = root / '.agents/coordination/runtime/REVIEWER.json'
try:
    reviewer = json.loads(runtime_path.read_text())
except (FileNotFoundError, json.JSONDecodeError):
    reviewer = {}
for line in (root / 'docs/agents/status.md').read_text().splitlines():
    match = row.match(line)
    if not match:
        continue
    task_id, owner, status, contract, delivery = (item.strip() for item in match.groups())
    if status != 'REVIEW_READY':
        continue
    # A completed review must be consumed by PM before the same task can run again.
    if reviewer.get('state') == 'review' and reviewer.get('task_id') == task_id:
        raise SystemExit(0)
    owner_config = registry.get(owner, {})
    print(task_id)
    print(contract)
    print(delivery)
    print(owner_config.get('worktree', ''))
    break
PY
)
[[ "${#task[@]}" -eq 4 ]] || exit 0
[[ -f "$project_root/${task[1]}" && -d "${task[3]}" ]] || exit 1

runner="$project_root/.agents/coordination/scripts/run_review_agent.sh"
"$systemd_run_bin" --user --unit="$unit" --collect --property=Type=exec \
  --working-directory="$project_root" \
  --setenv=PATH=/home/ubuntu/.local/share/mise/installs/node/24/bin:/usr/local/bin:/usr/bin:/bin \
  "$runner" "$project_root" "${task[0]}" "${task[1]}" "${task[2]}" "${task[3]}"

# Never publish working here. The supervised wrapper does so only after it starts.
"$systemctl_bin" --user is-active --quiet "$unit"
printf '{"state":"started","task_id":"%s","unit":"%s"}\n' "${task[0]}" "$unit" \
  >"$runtime/dispatch-REVIEWER.json"
