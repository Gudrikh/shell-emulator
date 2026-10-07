@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/vfs-minimal.csv" --prompt "ERROR> " --script "scripts/not-found.txt"