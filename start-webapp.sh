#!/usr/bin/env sh
# Works in WSL, Linux and macOS.  It intentionally uses the current Python so
# users do not need to remember the platform-specific virtualenv path.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$ROOT/start-webapp.py"
