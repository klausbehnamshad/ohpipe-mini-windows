# Einrichten: Hardware, Speicher, Netz, private Laufzeit, Pakete, Decoder,
# Modelle — Erfolg erst nach echter kurzer Verarbeitung (ASR + Diarisierung).
# Wiederholbar: fertige Schritte werden geprueft statt neu geladen.
# Veraendert keine bestehenden Python-Installationen, verlangt kein Admin.
# Aufruf (ohne globale ExecutionPolicy-Aenderung):
# powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Install.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
. "$root\scripts\common.ps1"
$cfg = Get-ModelsConfig $root
Write-Host "ohpipe-mini Windows-Setup $((Get-Content $root\VERSION -Raw).Trim())"
Show-Hardware
Test-DiskSpace -NeedGB 12
Test-Netz
Install-PythonEmbed -Root $root -Cfg $cfg
Install-PythonPakete -Root $root
Install-FFmpeg -Root $root -Cfg $cfg
Write-SetupState $root @{}
$py = Join-Path $root "runtime\python\python.exe"
Write-Host "Lade Modelle (einmalig, mit Groessenanzeige und Freigabehinweis) ..."
& $py "$root\scripts\Setup-Modelle.py"
if ($LASTEXITCODE -ne 0) { throw "Modell-Setup gescheitert (siehe Meldung oben). Kein Erfolg gemeldet." }
Add-UserPath -Dir (Join-Path $root "bin")
$daten = if ($env:OHPIPE_DATA) { $env:OHPIPE_DATA } `
  else { Join-Path $env:USERPROFILE "Downloads\ohpipe-mini" }
if ($env:OneDrive -and $daten.StartsWith($env:OneDrive,
    [StringComparison]::OrdinalIgnoreCase)) {
  Write-Host ("Hinweis: Der Datenordner liegt in OneDrive ($daten). Dessen Dienst " +
    "uebertraegt Dateien ins Netz. Fuer Interviews einen lokalen Ordner waehlen, " +
    "z. B. per Umgebungsvariable OHPIPE_DATA (siehe docs/DATENSCHUTZ.md).")
} else {
  Write-Host ("Hinweis: Ergebnisordner ausserhalb synchronisierter Ordner halten " +
    "(OneDrive u. ae. uebertragen Dateien ins Netz). Naeheres in docs/DATENSCHUTZ.md.")
}
Write-Host "Pruefe Decoder, Modelle und Laufzeit (Diagnose) ..."
& $py "$root\app\ohpipe.py" diagnose
if ($LASTEXITCODE -ne 0) { throw "Diagnose meldet fehlende Bestandteile (siehe oben). Kein Erfolg gemeldet." }
Write-Host "Selbsttest mit echter Verarbeitung (kurzer mitgelieferter Sprachclip) ..."
& $py "$root\tests\selbsttest_echt.py"
if ($LASTEXITCODE -ne 0) {
  throw ("Selbsttest mit echter Transkription/Sprechertrennung gescheitert. " +
    "Setup meldet bewusst keinen Erfolg (siehe Meldung oben).")
}
Write-Host ""
Write-Host "Setup fertig. Neues PowerShell-Fenster oeffnen, dann z. B.:"
Write-Host '  oh-kette "C:\Users\Name\Downloads\Interview.mp4"'
