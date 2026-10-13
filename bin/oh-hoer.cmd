@echo off
REM oh-hoer Starter (Windows).
setlocal
set "ROOT=%~dp0.."
"%ROOT%\runtime\python\python.exe" "%ROOT%\app\ohpipe.py" hoer %*
