# Deinstallation: entfernt Programmkomponenten; Aufnahmen/Ergebnisse/Modelle nur
# mit -MitDaten. Veraendert keine fremden Python-Installationen.
param([switch]$MitDaten)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$key = "HKCU:\Environment"
$cur = (Get-ItemProperty -Path $key -Name Path -ErrorAction SilentlyContinue).Path
if ($cur) {
  $neu = ($cur -split ";" | Where-Object { $_ -ne "$root\bin" }) -join ";"
  Set-ItemProperty -Path $key -Name Path -Value $neu
}
Remove-Item -Recurse -Force "$root\runtime" -ErrorAction SilentlyContinue
if ($MitDaten) { Remove-Item -Recurse -Force "$env:USERPROFILE\Downloads\ohpipe-mini" -ErrorAction SilentlyContinue }
else { Write-Host "Aufnahmen/Ergebnisse/Modelle bleiben erhalten (mit -MitDaten entfernen)." }
Write-Host "Deinstallation fertig."
