@echo off
cd /d "%~dp0"
python pdf_summarizer.py %*
pause
