@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --windowed --name "WhisperNetwork" --onefile main.py

echo Build complete. EXE is in dist\WhisperNetwork.exe
pause
