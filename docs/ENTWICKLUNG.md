# Entwicklung (ohpipe-mini-windows 0.3.0, Technik)

## Architektur

Medien --FFmpeg--> 16-kHz-WAV --faster-whisper--> Segmente + Wortzeiten.
pyannote-3.1 liefert Intervalle; `diar_adapter` + `diar2_merge` (Wortebene)
ergeben TXT/SRT/JSON/RTTM/Hoerliste/run.json. Mit `--voll` laeuft danach
`ohext` (regelbasiert, ohne Sprachmodell).

- `app/ohpipe.py`: Befehle, Import, Wiederaufnahme (`run.json` mit
  `schritte`-Instrumentierung), Exitcodes 0/2/3/4, Lock nur bei Selbsterwerb
  entfernt, eindeutige Interview-IDs, `.bak`-Sicherung, ASR-Cache.
- `app/diar_adapter.py`: Windows-Resultate auf diar2-Eingaben (Wort-JSON,
  RTTM), Fallback-Kennzeichnung, Hoerliste mit Gruenden, Rollenvorschlag,
  RTTM-Ableitung.
- `app/diar2_merge.py`: aus diar2 uebernommen (Commit `4ea28ce`,
  unveraendert; Herkunft `app/diar2_HERKUNFT.md`). Hier nicht umschreiben.
- `app/ohext.py`: Metadatenentwurf, Vorschlaege, PII-Pruefung, L1, Berichte.
- `app/models.json`: Python-, FFmpeg- und Modellrevisionen (fest).
- `app/requirements.lock`: 97 hash-gepruefte Wheels (win_amd64, CPython
  3.12, PyTorch-CPU-Index zuerst). Direkt fixiert zusaetzlich:
  torchaudio==2.3.1 (passend zu torch), pyannote-metrics==3.2.1 (sonst
  numpy-Konflikt), av==15.1.0 (av>=19 bricht faster-whisper 1.1.0),
  huggingface-hub==0.34.4 (hub>=1.0 bricht pyannote 3.3.2),
  pytest==8.3.4 (fuer smoke.cmd). torch bleibt 2.3.1 u. a. wegen
  Checkpoint-Kompatibilitaet (torch>=2.6 lehnt alte Checkpoints per
  `weights_only`-Vorgabe ab).
- `scripts/`: `common.ps1` (Laufzeit, Pakete, Decoder, Zustand),
  `Install.ps1` (Erfolg erst nach echter Verarbeitung), `Setup-Modelle.py`
  (Revisionen, Freigabehinweis, Cache-Vorabladung), `Uninstall.ps1`.
- `bin/`: `.cmd`- und `.ps1`-Starter auf das private Python.
- `tests/`: 39 pytest-Pruefungen (Logik, Adapter, Merge-Regression,
  Mock-Ablauf) + `selbsttest_echt.py` (echter Clip) + `tests/data/`.

## Build und Release

Version in `VERSION`. Paket aus dem Projektroot bauen (ohne `.venv`,
ohne `runtime`, ohne Daten — nur versendbare Dateien):

```powershell
python scripts/build_paket.py --ablage ..\Releases
```

Release-Artefakte: `ohpipe-mini-windows-<VERSION>.zip` + `.sha256` +
Releasebeschreibung (Nutzen, Einrichtung, gemessene Voraussetzungen,
Neuigkeiten, offene Punkte; vor Abnahme als Vorabversion).

## Versionsgeschichte

Das Repository ist mit `git init` vorbereitet (`.gitignore` schließt
`.venv`, `runtime`, Daten, Modelle und Geheimnisse aus). Geschichte und
Markierung legt der Betreuer ausdrücklich an:

```powershell
git add -A
git commit -m "ohpipe-mini-windows 0.3.0 (Vorabversion)"
git tag -a v0.3.0 -m "Vorabversion: keine Windows-Abnahme"
```

## Tests

`python -m pytest tests/ -q` (ohne Modelle, ohne Netz). Modelltests
(`selbsttest_echt.py`, Windows-Abnahme) sind eigene, tatsaechlich
ausgefuehrte Gruppen in `docs/TESTBERICHT.md`. CI (`.github/workflows/ci.yml`) installiert vorher die hash-gepruefte
Closure (`pip install --require-hashes -r app/requirements.lock`, gleiches
Kommando wie im Setup) und prueft auf Windows Programmlogik, Adaptertests
und Paketstruktur — keine Abnahme, kein Modelltest-Ersatz.
