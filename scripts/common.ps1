# Gemeinsame Setup-Funktionen fuer ohpipe-mini Windows.
# Echte Einrichtung: privates Python (embed), hash-gepruefte Pakete,
# FFmpeg aus privater Ablage, Modelle mit festen Revisionen.
# Kein Platzhalter: Jede Funktion laedt/prueft wirklich oder bricht mit
# konkreter Komponentenmeldung ab. Kein Erfolg ohne Pruefung.
# Aufruf nie mit geaenderter globaler ExecutionPolicy (siehe Install.ps1).

function Get-ModelsConfig([string]$Root) {
  $pfad = Join-Path $Root "app\models.json"
  if (!(Test-Path $pfad)) { throw "models.json fehlt ($pfad). Paket unvollstaendig." }
  return (Get-Content $pfad -Raw -Encoding utf8 | ConvertFrom-Json)
}

function Show-Hardware {
  $cs = Get-CimInstance Win32_ComputerSystem
  $os = Get-CimInstance Win32_OperatingSystem
  $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
  $ram = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
  Write-Host "CPU: $cpu | RAM: ${ram} GB | OS: $($os.Caption) $($os.Version)"
  $gpu = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name
  Write-Host "Grafik: $($gpu -join '; ')"
  Write-Host "Profil: CPU x64 Standard (CUDA optional, nie Voraussetzung)."
}

function Test-DiskSpace([int]$NeedGB = 12) {
  $d = (Get-Item $env:USERPROFILE).PSDrive
  $free = [math]::Round((Get-PSDrive $d.Name).Free / 1GB, 1)
  Write-Host "Frei auf ${d}: ${free} GB (benoetigt ca. ${NeedGB} GB inkl. Modelle)."
  if ($free -lt $NeedGB) { throw "Zu wenig Speicherplatz. Bitte Platz schaffen." }
}

function Test-Netz([string]$Url = "https://www.python.org/ftp/python/") {
  try {
    $r = Invoke-WebRequest -Uri $Url -Method Head -TimeoutSec 20 -UseBasicParsing
    if ($r.StatusCode -ge 400) { throw "HTTP $($r.StatusCode)" }
  } catch {
    throw ("Paketnetz fehlt ($Url nicht erreichbar: {0}). Setup braucht genau einmal Netz " +
      "fuer Laufzeit, Pakete, Decoder und Modelle. Danach laeuft alles offline." -f $_.Exception.Message)
  }
}

function Invoke-VerifiedDownload([string]$Url, [string]$Ziel, [string]$ErwartetSha256,
                                 [string]$Komponente) {
  $mb = 0
  try { $mb = [math]::Round((Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec 30).Headers.'Content-Length'[0] / 1MB, 1) } catch {}
  if ($mb -gt 0) { Write-Host "$Komponente : $Url (ca. $mb MB) ..." } else { Write-Host "$Komponente : $Url ..." }
  $tmp = "$Ziel.part"
  if (Test-Path $tmp) { Remove-Item -Force $tmp }
  # curl.exe ist in Windows 10/11 enthalten; -C - setzt Abbrueche fort.
  $curl = (Get-Command curl.exe -ErrorAction SilentlyContinue).Source
  if ($curl) {
    & $curl -sSL -C - --retry 3 --retry-all-errors -o $tmp $Url
    if ($LASTEXITCODE -ne 0) { throw "${Komponente}: Download abgebrochen (curl Exit $LASTEXITCODE)." }
  } else {
    Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing
  }
  Move-Item -Force $tmp $Ziel
  $hash = (Get-FileHash $Ziel -Algorithm SHA256).Hash.ToLower()
  if ($hash -ne $ErwartetSha256.ToLower()) {
    Remove-Item -Force $Ziel -ErrorAction SilentlyContinue
    throw ("${Komponente}: Pruefsumme falsch (erwartet $ErwartetSha256, erhalten $hash). " +
      "Datei verworfen; Setup abgebrochen.")
  }
  Write-Host "$Komponente : Pruefsumme ok."
}

function Install-PythonEmbed([string]$Root, $Cfg) {
  $ziel = Join-Path $Root "runtime\python"
  $exe = Join-Path $ziel "python.exe"
  if ((Test-Path $exe) -and (Test-Path (Join-Path $ziel "Lib\site-packages\pip"))) {
    $v = & $exe -c "import sys; print('.'.join(map(str,sys.version_info[:3])))" 2>$null
    if ($v -eq $Cfg.python.version) { Write-Host "Privates Python $($Cfg.python.version) vorhanden — uebersprungen."; return }
    Write-Host "Privates Python hat Version $v (erwartet $($Cfg.python.version)) — neu eingerichtet."
  }
  $url = "https://www.python.org/ftp/python/$($Cfg.python.version)/$($Cfg.python.embed)"
  $zip = Join-Path ([IO.Path]::GetTempPath()) $Cfg.python.embed
  Invoke-VerifiedDownload $url $zip $Cfg.python.embed_sha256 "Privates Python $($Cfg.python.version)"
  if (Test-Path $ziel) { Remove-Item -Recurse -Force $ziel }
  New-Item -ItemType Directory -Force $ziel | Out-Null
  Expand-Archive -Path $zip -DestinationPath $ziel -Force
  Remove-Item -Force $zip -ErrorAction SilentlyContinue
  # Embed-Python: site-Pakete freischalten (Datei pythonXY._pth).
  $pth = Get-ChildItem $ziel -Filter "python*._pth" | Select-Object -First 1
  if ($pth) {
    $inhalt = Get-Content $pth.FullName -Raw -Encoding ascii
    if ($inhalt -match "#import site") {
      $inhalt -replace "#import site", "import site" | Set-Content $pth.FullName -Encoding ascii
    }
    # Anwendungsordner fest einbinden (isolierte Laufzeit: kein Skriptordner
    # im Modulpfad). Zweite Absicherung neben sys.path in app/ohpipe.py;
    # nach einem Verschieben des Ordners Setup erneut starten.
    $appPfad = Join-Path $Root "app"
    if ((Get-Content $pth.FullName -Encoding ascii) -notcontains $appPfad) {
      Add-Content $pth.FullName $appPfad -Encoding ascii
    }
  }
  # pip einrichten (Setup hat Netz; Version wird in state.json festgehalten).
  $getpip = Join-Path ([IO.Path]::GetTempPath()) "ohpipe-get-pip.py"
  Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip -UseBasicParsing
  & $exe $getpip --no-warn-script-location
  if ($LASTEXITCODE -ne 0) { throw "pip-Einrichtung im privaten Python gescheitert." }
  Remove-Item -Force $getpip -ErrorAction SilentlyContinue
  $pv = & $exe -m pip --version
  Write-Host "Privates Python bereit ($pv)."
}

function Install-PythonPakete([string]$Root) {
  $exe = Join-Path $Root "runtime\python\python.exe"
  if (!(Test-Path $exe)) { throw "Privates Python fehlt (runtime\python\python.exe). Erst Install-PythonEmbed." }
  $lock = Join-Path $Root "app\requirements.lock"
  if (!(Test-Path $lock)) { throw "requirements.lock fehlt. Paket unvollstaendig." }
  $anzahl = (Select-String -Path $lock -Pattern "^    --hash" | Measure-Object).Count
  Write-Host "Installiere $anzahl festgelegte Pakete (hash-geprueft, CPU-Variante) ..."
  Push-Location $Root
  try {
    & $exe -m pip install --require-hashes -r "app\requirements.lock"
    if ($LASTEXITCODE -ne 0) { throw "Paketinstallation gescheitert (siehe pip-Fehler oben)." }
    & $exe -c "import faster_whisper, pyannote.audio, torch; print('Imports ok:', torch.__version__)"
    if ($LASTEXITCODE -ne 0) { throw "Importpruefung (faster-whisper/pyannote/torch) gescheitert." }
  } finally { Pop-Location }
  Write-Host "Python-Pakete eingerichtet und geprueft."
}

function Install-FFmpeg([string]$Root, $Cfg) {
  $ziel = Join-Path $Root "runtime\ffmpeg"
  $exe = Join-Path $ziel "bin\ffmpeg.exe"
  $probe = Join-Path $ziel "bin\ffprobe.exe"
  if ((Test-Path $exe) -and (Test-Path $probe)) {
    $v = & $exe -version 2>$null | Select-Object -First 1
    if ($v -match [regex]::Escape($Cfg.ffmpeg.version)) {
      Write-Host "FFmpeg $($Cfg.ffmpeg.version) vorhanden — uebersprungen."
      return
    }
    Write-Host "FFmpeg-Version weicht ab ($v) — neu eingerichtet."
  }
  Write-Host ("Decoder: $($Cfg.ffmpeg.variante). Lizenzhinweis: statischer Build, " +
    "enthaelt GPLv3-Komponenten (nur ffmpeg.exe/ffprobe.exe genutzt, siehe docs/LIZENZEN.md).")
  $zip = Join-Path ([IO.Path]::GetTempPath()) "ohpipe-ffmpeg.zip"
  Invoke-VerifiedDownload $Cfg.ffmpeg.url $zip $Cfg.ffmpeg.sha256 "FFmpeg $($Cfg.ffmpeg.version)"
  if (Test-Path $ziel) { Remove-Item -Recurse -Force $ziel }
  New-Item -ItemType Directory -Force $ziel | Out-Null
  $tmp = Join-Path ([IO.Path]::GetTempPath()) "ohpipe-ffmpeg-entpackt"
  if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
  Expand-Archive -Path $zip -DestinationPath $tmp -Force
  Remove-Item -Force $zip -ErrorAction SilentlyContinue
  $innen = Get-ChildItem $tmp -Directory | Select-Object -First 1
  Copy-Item (Join-Path $innen.FullName "*") $ziel -Recurse -Force
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
  $fv = & $exe -version | Select-Object -First 1
  $pv = & $probe -version | Select-Object -First 1
  if ($LASTEXITCODE -ne 0) { throw "FFmpeg-Pruefung gescheitert ($fv / $pv)." }
  Write-Host "Decoder bereit ($fv)."
  Write-Host "Der Programmprozess nutzt diese Ablage unabhaengig von System-FFmpeg."
}

function Write-SetupState([string]$Root, [hashtable]$Abschnitt) {
  $pfad = Join-Path $Root "runtime\state.json"
  $state = @{}
  if (Test-Path $pfad) {
    # Ohne -AsHashtable (gibt es erst ab PowerShell 6; 5.1-kompatibel lesen).
    try {
      (Get-Content $pfad -Raw -Encoding utf8 | ConvertFrom-Json).PSObject.Properties |
        ForEach-Object { $state[$_.Name] = $_.Value }
    } catch {}
  }
  foreach ($k in $Abschnitt.Keys) { $state[$k] = $Abschnitt[$k] }
  $state["version"] = (Get-Content (Join-Path $Root "VERSION") -Raw -Encoding utf8).Trim()
  $state["datum"] = (Get-Date).ToString("yyyy-MM-dd")
  New-Item -ItemType Directory -Force (Split-Path $pfad) | Out-Null
  ($state | ConvertTo-Json -Depth 8) | Set-Content $pfad -Encoding utf8
}

function Add-UserPath([string]$Dir) {
  $key = "HKCU:\Environment"
  $cur = (Get-ItemProperty -Path $key -Name Path -ErrorAction SilentlyContinue).Path
  if ($cur -split ";" -contains $Dir) { Write-Host "PATH enthaelt bin bereits."; return }
  Set-ItemProperty -Path $key -Name Path -Value "$cur;$Dir"
  Write-Host "Benutzer-PATH ergaenzt (kontrolliert, ohne Ueberschreiben). Terminal neu starten."
}
