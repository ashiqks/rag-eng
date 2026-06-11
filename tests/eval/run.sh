#!/usr/bin/env bash
# Activate the venv and run the Vertex AI Search evaluation harness.
#
# Forwards all arguments verbatim to run_eval.py:
#   ./run.sh
#   ./run.sh --dry-run
#   ./run.sh --search-engine-id my-other-engine --concurrency 4
#
# HTTPS_PROXY etc. are loaded from .env automatically by run_eval.py
# (python-dotenv). No manual proxy export needed.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

VENV_PY="$SCRIPT_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "Virtual environment not found at $VENV_PY. Run ./setup.sh first." >&2
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    echo "WARNING: .env not found - copy .env.example to .env and edit it." >&2
fi

exec "$VENV_PY" "$SCRIPT_DIR/run_eval.py" "$@"
