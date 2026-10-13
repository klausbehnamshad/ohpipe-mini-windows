@echo off
REM Rauchtest mit der privaten Laufzeit: Entwicklungspruefungen + echter Selbsttest.
REM Fehler werden als Exitcode weitergegeben (kein Erfolg nach Fehlschlag).
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\runtime\python\python.exe"
if not exist "%PY%" (
  echo FEHLER: Privates Python fehlt (%PY%^).
  echo Bitte zuerst einrichten: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Install.ps1
  exit /b 2
)
"%PY%" -m pytest tests\ -q
if errorlevel 1 (
  echo FEHLER: Entwicklungspruefungen gescheitert.
  exit /b 1
)
"%PY%" tests\selbsttest_echt.py
if errorlevel 1 (
  echo FEHLER: Echter Selbsttest gescheitert (siehe oben^).
  exit /b 1
)
echo SMOKE OK (Entwicklungspruefungen + echte ASR/Diarisierung).
