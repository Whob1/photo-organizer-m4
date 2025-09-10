#!/usr/bin/env zsh
# Bootstraps virtualenv, installs deps, checks tooling, and runs the CLI
set -euo pipefail

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"
PY_BIN="python3"

if [ ! -d "$VENV_DIR" ]; then
  echo "[bootstrap] Creating virtualenv at $VENV_DIR"
  $PY_BIN -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools

# Editable install
pip install -e .

# Tool checks
command -v ffmpeg >/dev/null 2>&1 || echo "[bootstrap] WARNING: ffmpeg not found; video processing may fail."
command -v rclone >/dev/null 2>&1 || echo "[bootstrap] WARNING: rclone not found; Google Photos operations may fail."

# Ensure dirs
photoorg setup || true

# Pass all args to CLI
exec photoorg "$@"

