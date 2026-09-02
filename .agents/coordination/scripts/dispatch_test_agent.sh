#!/usr/bin/env bash
set -euo pipefail
project_root="${1:?usage: dispatch_test_agent.sh PROJECT_ROOT}"
runtime="$project_root/.agents/coordination/runtime"
systemctl_bin="${SYSTEMCTL_BIN:-systemctl}"
systemd_run_bin="${SYSTEMD_RUN_BIN:-systemd-run}"
mkdir -p "$runtime"
readarray -t task < <(python3 - "$project_root" <<'PY'
import json,re,sys
from pathlib import Path
root=Path(sys.argv[1]); agents=json.loads((root/'.agents/coordination/agents.json').read_text())['agents']
row=re.compile(r"^\|\s*`?([^|`]+)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*`?([^|`]+)`?\s*\|\s*`?([^|`]+)`?")
for line in (root/'docs/agents/status.md').read_text().splitlines():
 m=row.match(line)
 if not m or m.group(3).strip()!='TEST_READY': continue
 task,owner,_,contract,delivery=(x.strip() for x in m.groups())
 completion=root/f'.agents/coordination/runtime/test-completed-{task}.json'
 try: done=json.loads(completion.read_text())
 except (FileNotFoundError,json.JSONDecodeError): done={}
 if done.get('state')=='completed' and done.get('delivery')==delivery: continue
 domain=owner.removeprefix('WORKER_'); tester=f'TESTER_{domain}'
 cfg=agents.get(tester)
 if cfg: print('\n'.join((task,owner,tester,contract,delivery,cfg.get('worktree',''),cfg.get('model','gpt-5.6-terra'),cfg.get('reasoning_effort','medium')))); break
PY
)
[[ "${#task[@]}" -eq 8 ]] || exit 0
unit="cs-board-agent-${task[2],,}.service"
exec 7>"$runtime/dispatch-${task[2]}.lock"; flock -n 7 || exit 0
"$systemctl_bin" --user is-active --quiet "$unit" && exit 0
"$systemd_run_bin" --user --unit="$unit" --collect --property=Type=exec --working-directory="$project_root" \
  --setenv=PATH=/home/ubuntu/.local/share/mise/installs/node/24/bin:/usr/local/bin:/usr/bin:/bin \
  "$project_root/.agents/coordination/scripts/run_test_agent.sh" "$project_root" "${task[@]}"
"$systemctl_bin" --user is-active --quiet "$unit"
