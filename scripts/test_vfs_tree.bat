@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/vfs-tree.csv" --prompt "TREE> " --script "scripts/startup.txt"