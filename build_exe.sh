#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --windowed --name WhisperNetwork --onefile main.py

echo "Build complete: dist/WhisperNetwork"
