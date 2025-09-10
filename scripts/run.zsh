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

# Apple Silicon hints
if sysctl -n machdep.cpu.brand_string | grep -qi "Apple"; then
  export PYTORCH_ENABLE_MPS_FALLBACK=1
  echo "[bootstrap] Apple Silicon detected. If PyTorch is installed, MPS fallback is enabled."
fi

# Optional install for Restormer (PyTorch) if enabled via env
if [ "${PHOTOORG_AI_RESTORMER:-1}" = "1" ]; then
  if ! python -c 'import torch; import importlib; importlib.import_module("basicsr.archs.restormer_arch")' >/dev/null 2>&1; then
    echo "[bootstrap] Installing PyTorch + Restormer (this may take a while)"
    pip install --upgrade 'torch' 'torchvision' 'torchaudio' || true
    pip install --upgrade 'git+https://github.com/swz30/Restormer.git' || true
  fi
fi

# Ensure dirs and models
photoorg setup || true
photoorg setup-models || true

# Default to `run` if no args were provided
if [ $# -eq 0 ]; then
  set -- run
fi
# Pass all args to CLI
exec photoorg "$@"

