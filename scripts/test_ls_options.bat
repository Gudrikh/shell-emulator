@echo off
cd /d "%~dp0.."
python -m src.main --vfs "data/vfs-ls.csv" --prompt "LS> " --script "scripts/startup_ls_options.txt"
