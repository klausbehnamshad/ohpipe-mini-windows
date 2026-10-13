@echo off
REM oh-status Starter (Windows).
setlocal
set "ROOT=%~dp0.."
"%ROOT%\runtime\python\python.exe" "%ROOT%\app\ohpipe.py" status %*
