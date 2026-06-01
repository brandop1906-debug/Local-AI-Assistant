@echo off
cd /d "%~dp0"
python quote_generator.py %*
pause
