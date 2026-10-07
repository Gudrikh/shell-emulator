@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/vfs-minimal.csv" --prompt "CONFIG> " --script "scripts/startup.txt"