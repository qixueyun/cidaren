@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
"%~dp0runtime\python.exe" "%~dp0portable_check.py"
pause
