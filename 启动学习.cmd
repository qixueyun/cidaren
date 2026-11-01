@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0runtime\python.exe" (
  "%~dp0runtime\python.exe" "%~dp0launcher.py"
) else (
  python "%~dp0launcher.py"
)
if errorlevel 1 pause
