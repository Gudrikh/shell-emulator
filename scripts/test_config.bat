@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/test-vfs.csv" --prompt "CONFIG> " --script "scripts/startup.txt"