#!/usr/bin/env bash
# Safe default: read-only preflight. See docs/foo-runner.md before registration.
set +x
set -euo pipefail
umask 077
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SCRIPT_DIR/runner_host_setup.py" "$@"
