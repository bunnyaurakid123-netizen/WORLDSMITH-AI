#!/usr/bin/env bash
set -euo pipefail
# Build a Windows GUI EXE from Linux using a Windows Python environment under Wine.
# PyInstaller itself is not a native cross-compiler; Wine must run a real Windows Python/PyInstaller environment.
ROOT="$(cd "$(dirname "$0")" && pwd)"
WINEPREFIX="${WINEPREFIX:-$ROOT/.wine-worldsmith}"
WINPY="${WINPY:-C:/Python311/python.exe}"
export WINEPREFIX
command -v wine >/dev/null || { echo "ERROR: wine is required."; exit 1; }
[ -f "$ROOT/worldsmith/__main__.py" ] || { echo "ERROR: run from repository root."; exit 1; }
mkdir -p "$ROOT/dist" "$ROOT/build"

echo "[1/4] Checking Wine Windows Python..."
wine "$WINPY" -c "import sys; print(sys.version); print(sys.platform)"

echo "[2/4] Installing project dependencies into the Windows Python environment..."
wine "$WINPY" -m pip install -U pip setuptools wheel
wine "$WINPY" -m pip install -e "$ROOT"
wine "$WINPY" -m pip install -U pyinstaller

echo "[3/4] Building GUI EXE..."
wine "$WINPY" -m PyInstaller --noconfirm --clean --onefile --windowed --name WorldSmith --paths "$ROOT" "$ROOT/worldsmith/__main__.py"

echo "[4/4] Checking output..."
[ -f "$ROOT/dist/WorldSmith.exe" ] || { echo "ERROR: dist/WorldSmith.exe was not produced."; exit 1; }
echo "SUCCESS: $ROOT/dist/WorldSmith.exe"
