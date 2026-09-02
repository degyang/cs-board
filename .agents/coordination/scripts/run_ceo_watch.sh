#!/usr/bin/env bash
set -euo pipefail
project_root="${1:?usage: run_ceo_watch.sh PROJECT_ROOT}"
dashboard_dir="${TEAM_DASHBOARD_DIR:-/home/ubuntu/.codex/skills/pos-magents/scripts/team-dashboard}"
node_bin="${NODE_BIN:-/home/ubuntu/.local/share/mise/installs/node/24/bin/node}"
teamctl="$dashboard_dir/teamctl.mjs"
probe="$project_root/.agents/coordination/scripts/pm_event_probe.py"
systemctl_bin="${SYSTEMCTL_BIN:-systemctl}"
finish() { "$node_bin" "$teamctl" agent --project "$project_root" --role CEO --state idle >/dev/null 2>&1 || true; }
trap finish EXIT
"$node_bin" "$teamctl" agent --project "$project_root" --role CEO --state working --task GLOBAL-WATCH --cycle 监督 --attempt 1 --lease-seconds 90 >/dev/null
event="$(python3 "$probe" probe --project "$project_root" --max-actions 1)"
if [[ -n "$event" ]]; then
  "$systemctl_bin" --user start --no-block cs-board-pm.service >/dev/null 2>&1 || true
fi
