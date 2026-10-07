@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/vfs-many.csv" --prompt "MANY> " --script "scripts/startup.txt"