@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/vfs-stage4.csv" --prompt "STAGE5> " --script "scripts/startup_stage5.txt"