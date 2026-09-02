#!/usr/bin/env bash
set -euo pipefail
root="${1:?usage: dispatch_tracked_worker.sh PROJECT_ROOT}"
readarray -t task < <(python3 - "$root" <<'PY'
import sys
from pathlib import Path
root=Path(sys.argv[1])
for line in (root/'docs/agents/status.md').read_text().splitlines():
 cells=[x.strip().strip('`') for x in line.split('|')[1:-1]]
 if len(cells)>=4 and cells[2]=='DISPATCHED': print('\n'.join((cells[0],cells[1],cells[3]))); break
PY
)
[[ "${#task[@]}" -eq 3 ]] || exit 0
commit="$(git -C "$root" rev-parse HEAD)"
"$root/.agents/coordination/scripts/dispatch_cli_agent.sh" "$root" "${task[1]}" "${task[0]}" "${task[2]}" "$commit"
