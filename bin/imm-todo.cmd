@echo off
REM imm-todo Starter (Windows).
setlocal
set "ROOT=%~dp0.."
"%ROOT%\runtime\python\python.exe" "%ROOT%\app\ohpipe.py" imm-todo %*
