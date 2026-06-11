"""Cross-platform launcher for the Vertex AI Search evaluation harness.

This is the single entry point for running the eval on Windows, Linux, or
macOS. It detects your OS, creates a local virtual environment if one does
not exist yet, installs (or refreshes) the requirements on first run, and
then re-execs `run_eval.py` inside the venv with whatever arguments you
passed.

Usage (from the repo root or from anywhere):

    python tests/eval/eval.py                   # full eval
    python tests/eval/eval.py --dry-run         # query the app, skip scoring
    python tests/eval/eval.py --search-engine-id my-engine --concurrency 4

The first run takes a minute or two (creating the venv + installing deps).
Subsequent runs are instant.

Requires Python 3.10+ on PATH and (for production runs) a `gcloud` ADC
session - see the README for the one-time auth steps.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_DIR = HERE / ".venv"
REQUIREMENTS = HERE / "requirements.txt"
ENV_EXAMPLE = HERE / ".env.example"
ENV_FILE = HERE / ".env"
SETUP_MARKER = VENV_DIR / ".eval_harness_setup_ok"
RUN_EVAL = HERE / "run_eval.py"

MIN_PY = (3, 10)


def _color(code: str, msg: str) -> str:
    if not sys.stdout.isatty():
        return msg
    return f"\033[{code}m{msg}\033[0m"


def step(msg: str) -> None:
    print(_color("1;36", f"==> {msg}"))


def ok(msg: str) -> None:
    print(_color("0;32", f"    {msg}"))


def warn(msg: str) -> None:
    print(_color("0;33", f"    {msg}"))


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def check_python_version() -> None:
    if sys.version_info < MIN_PY:
        sys.exit(
            f"Python {sys.version.split()[0]} is too old. "
            f"This harness requires Python {MIN_PY[0]}.{MIN_PY[1]}+."
        )


def venv_is_corrupted() -> bool:
    """Heuristic: a fresh venv has no '~*' stub directories from interrupted installs."""
    site_packages = (
        VENV_DIR / ("Lib/site-packages" if platform.system() == "Windows" else "")
    )
    if platform.system() != "Windows":
        # Linux/macOS: lib/pythonX.Y/site-packages
        for child in (VENV_DIR / "lib").glob("python*"):
            site_packages = child / "site-packages"
            break
    if not site_packages.exists():
        return False
    return any(p.name.startswith("~") for p in site_packages.iterdir())


def create_venv() -> None:
    step(f"Creating virtual environment at {VENV_DIR}")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    ok("venv created")


def install_requirements() -> None:
    step("Installing requirements (this takes ~1-2 min on first run)")
    # Note: we deliberately skip `pip install --upgrade pip`. On Windows
    # (especially Python 3.14) pip's self-upgrade can hit a file lock on its
    # own _vendor dir mid-replace.
    subprocess.check_call(
        [str(venv_python()), "-m", "pip", "install", "-r", str(REQUIREMENTS), "--quiet"]
    )
    ok("Dependencies installed")


def bootstrap_env_file() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE.exists():
        return
    shutil.copy2(ENV_EXAMPLE, ENV_FILE)
    warn(f".env created from .env.example - EDIT IT before the next run:")
    warn(f"  {ENV_FILE}")


def check_gcloud() -> None:
    if shutil.which("gcloud") is None:
        warn("gcloud CLI not found on PATH (https://cloud.google.com/sdk/docs/install).")
        warn("You'll need it to authenticate before running a real eval.")
        return
    try:
        out = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15,
        ).strip()
        if out:
            ok(f"ADC token available ({len(out)} chars)")
            return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    warn("Application Default Credentials not set. Run:")
    warn("  gcloud auth application-default login")
    warn("  gcloud auth application-default set-quota-project <your-project-id>")


def needs_setup() -> bool:
    return not venv_python().exists() or not SETUP_MARKER.exists()


def setup() -> None:
    check_python_version()
    step(f"Detected OS: {platform.system()} {platform.release()}")
    step(f"System Python: {sys.version.split()[0]} at {sys.executable}")

    if VENV_DIR.exists() and venv_is_corrupted():
        warn("Existing venv is corrupted - recreating.")
        shutil.rmtree(VENV_DIR)

    if not venv_python().exists():
        create_venv()
    else:
        step(f"Using existing virtual environment at {VENV_DIR}")

    install_requirements()
    bootstrap_env_file()
    check_gcloud()
    SETUP_MARKER.write_text("ok\n", encoding="utf-8")
    step("Setup complete.")


def run_eval(forwarded: list[str]) -> int:
    if not RUN_EVAL.exists():
        sys.exit(f"ERROR: {RUN_EVAL} not found.")
    cmd = [str(venv_python()), str(RUN_EVAL), *forwarded]
    # On POSIX we exec to replace the current process; on Windows we spawn
    # and return its exit code.
    if platform.system() == "Windows":
        return subprocess.call(cmd)
    os.execv(cmd[0], cmd)  # noqa: S606 - intentional, replaces this process
    return 0  # unreachable


def main() -> int:
    forwarded = sys.argv[1:]
    if needs_setup():
        setup()
    elif "--reinstall" in forwarded:
        forwarded.remove("--reinstall")
        SETUP_MARKER.unlink(missing_ok=True)
        setup()
    return run_eval(forwarded)


if __name__ == "__main__":
    sys.exit(main())
