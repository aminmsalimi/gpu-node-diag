#!/usr/bin/env bash
set -euo pipefail

REPO="aminmsalimi/gpu-node-diag"
REF="${GDIAG_REF:-main}"
INSTALL_ROOT="${GDIAG_HOME:-$HOME/.local/share/gpunodediag}"
BIN_DIR="${GDIAG_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
PACKAGE_URL="https://github.com/${REPO}/archive/refs/heads/${REF}.zip"

if [[ "$REF" == v* ]]; then
    PACKAGE_URL="https://github.com/${REPO}/archive/refs/tags/${REF}.zip"
fi

printf '\nGPUNodeDiag installer\n\n'

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 was not found."
    echo "GPUNodeDiag requires Python 3.10 or newer."
    exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(
        f"ERROR: GPUNodeDiag requires Python 3.10+. "
        f"Detected {sys.version.split()[0]}"
    )
print(f"✓ Python {sys.version.split()[0]}")
PY

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"

if [[ ! -d "$VENV" ]]; then
    echo "→ Creating isolated environment"
    if ! python3 -m venv "$VENV"; then
        echo "ERROR: Could not create a Python virtual environment."
        echo "On Ubuntu/Debian, install python3-venv and retry."
        exit 1
    fi
fi

echo "→ Installing GPUNodeDiag from GitHub ($REF)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install     --quiet     --upgrade     --force-reinstall     --no-cache-dir     "$PACKAGE_URL"

ln -sf "$VENV/bin/gdiag" "$BIN_DIR/gdiag"

echo
"$VENV/bin/gdiag" --version
echo
echo "✓ Installed: $BIN_DIR/gdiag"

case ":$PATH:" in
    *":$BIN_DIR:"*)
        echo "✓ Run: gdiag"
        ;;
    *)
        echo
        echo "Add this to your shell profile:"
        echo '  export PATH="$HOME/.local/bin:$PATH"'
        echo
        echo "Then run:"
        echo "  gdiag"
        ;;
esac
