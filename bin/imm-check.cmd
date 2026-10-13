@echo off
REM imm-check Starter (Windows).
setlocal
set "ROOT=%~dp0.."
"%ROOT%\runtime\python\python.exe" "%ROOT%\app\ohpipe.py" imm-check %*
