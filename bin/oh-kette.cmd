@echo off
REM oh-kette Starter (Windows). Ruft privates Python ohne globale Policy-Aenderung.
setlocal
set "ROOT=%~dp0.."
"%ROOT%\runtime\python\python.exe" "%ROOT%\app\ohpipe.py" kette %*
