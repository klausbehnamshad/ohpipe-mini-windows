@echo off
REM oh-uebernehmen Starter (Windows).
setlocal
set "ROOT=%~dp0.."
"%ROOT%\runtime\python\python.exe" "%ROOT%\app\ohpipe.py" uebernehmen %*
