#!/usr/bin/env bash
# One-shot setup for the Vertex AI Search evaluation harness on Linux/macOS.
#
#   1. Verifies Python 3.10+ is on PATH.
#   2. Creates a local virtual environment at tests/eval/.venv (idempotent).
#   3. Installs / upgrades requirements.txt.
#   4. Bootstraps .env from .env.example if it does not exist yet.
#   5. Reports gcloud / ADC status (does NOT log you in - that's interactive).
#
# Usage:
#   cd tests/eval
#   ./setup.sh
#   PYTHON_EXE=python3.12 ./setup.sh   # override interpreter

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

PYTHON_EXE="${PYTHON_EXE:-python3}"

# Colours (only when stdout is a TTY)
if [[ -t 1 ]]; then
    C_STEP=$'\033[1;36m'; C_OK=$'\033[0;32m'; C_WARN=$'\033[0;33m'; C_OFF=$'\033[0m'
else
    C_STEP=''; C_OK=''; C_WARN=''; C_OFF=''
fi
step() { printf "%s==> %s%s\n" "$C_STEP" "$1" "$C_OFF"; }
ok()   { printf "%s    %s%s\n" "$C_OK"   "$1" "$C_OFF"; }
warn() { printf "%s    %s%s\n" "$C_WARN" "$1" "$C_OFF"; }

# --- 1. Python ---------------------------------------------------------------
step "Checking Python"
if ! command -v "$PYTHON_EXE" &>/dev/null; then
    echo "Python executable '$PYTHON_EXE' not found. Install Python 3.10+ or override with PYTHON_EXE=..." >&2
    exit 1
fi
PY_VER="$("$PYTHON_EXE" -c 'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))')"
"$PYTHON_EXE" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || {
    echo "Python $PY_VER is too old. Need 3.10+." >&2
    exit 1
}
ok "Python $PY_VER at $(command -v "$PYTHON_EXE")"

# --- 2. Virtual environment --------------------------------------------------
VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"

# Detect a corrupted venv (interrupted pip install can leave ~* stubs).
if [[ -d "$VENV_DIR" ]]; then
    if compgen -G "$VENV_DIR/lib/python*/site-packages/~*" > /dev/null || [[ ! -x "$VENV_PY" ]]; then
        warn "Existing venv is corrupted - recreating."
        rm -rf "$VENV_DIR"
    fi
fi

if [[ ! -x "$VENV_PY" ]]; then
    step "Creating virtual environment at $VENV_DIR"
    "$PYTHON_EXE" -m venv "$VENV_DIR"
    ok "venv created"
else
    step "Using existing virtual environment at $VENV_DIR"
fi

# --- 3. Dependencies ---------------------------------------------------------
step "Installing requirements"
# We deliberately skip `pip install --upgrade pip` here. On some platforms
# pip's self-upgrade hits a file-lock on its own _vendor dir mid-replace.
# The pip bundled with venv is fine for installing the requirements below.
"$VENV_PY" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
ok "Dependencies installed"

# --- 4. .env -----------------------------------------------------------------
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
step "Checking .env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn ".env created from .env.example - EDIT IT before running:"
    warn "  \$EDITOR $ENV_FILE"
else
    ok ".env already exists"
fi

# --- 5. gcloud / ADC ---------------------------------------------------------
step "Checking gcloud + ADC"
if ! command -v gcloud &>/dev/null; then
    warn "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
else
    ACTIVE_ACCT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"
    if [[ -z "$ACTIVE_ACCT" ]]; then
        warn "No active gcloud account. Run:  gcloud auth login <your-email>"
    else
        ok "Active account: $ACTIVE_ACCT"
    fi
    if TOK="$(gcloud auth application-default print-access-token 2>/dev/null)" && [[ -n "$TOK" ]]; then
        ok "ADC token available (${#TOK} chars)"
    else
        warn "Application Default Credentials not set. Run:"
        warn "  gcloud auth application-default login"
        warn "  gcloud auth application-default set-quota-project <your-project-id>"
    fi
fi

echo
step "Setup complete."
echo "Next:"
echo "  1. Edit .env (project id, search engine id, proxy if needed)"
echo "  2. Run the eval:    ./run.sh"
echo "  3. Or dry-run:      ./run.sh --dry-run"
