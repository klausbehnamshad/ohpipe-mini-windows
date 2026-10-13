# Changelog (ohpipe-mini-windows)

## 0.3.2 (2026-10-13, Entwicklungsstand — keine Windows-Abnahme)

- Doppelte Rollen in `--setzt` werden abgewiesen (zuvor still
  überschrieben); Regressionstest.
- Windows-CI installiert die Testvoraussetzungen reproduzierbar aus dem
  Hash-Lock (gleiches Kommando wie im Setup).
- 39 pytest-Prüfungen.

## 0.3.1 (2026-10-13, Entwicklungsstand — keine Windows-Abnahme)

- Prüfbericht-Korrekturen: `${Komponente}`-Syntax, CI-Parsercheck für alle
  Skripte, isolierter Start (App-Ordner fest eingebunden + `._pth`),
  `--setzt`-Parsing/Validierung, `--tausch` als reiner Rollentausch,
  OneDrive-Hinweis, `.gitignore` im Paket.
- Sprachmodellerweiterung bleibt ausdrücklich regelbasiert (offen).
- 38 pytest-Prüfungen (neu: isolierter Start, Rollen-Konsistenz).

## 0.3.0 (2026-10-13, Entwicklungsstand — keine Windows-Abnahme)

- Echte Einrichtung: privates Python 3.12.10 (hash-geprüft), 97 hash-geprüfte
  Pakete (CPU-Variante, `app/requirements.lock`), FFmpeg 8.1.2 (hash-geprüft),
  Modelle mit festen Revisionen (`app/models.json`), Setup-Erfolg erst nach
  echter kurzer Verarbeitung.
- Wortweise Sprecherzuordnung: `diar2_merge.py` aus diar2 (Commit `4ea28ce`,
  unverändert, Apache-2.0) über `app/diar_adapter.py`; echte Wortzeiten aus
  faster-whisper, gekennzeichneter Rückfall ohne Wortzeiten.
- JSON-Format 2 (Wörter mit Zeitquelle, Sätze, Turns, Rollenvorschlag, RTTM
  als `NAME.rttm`); Format 1 bleibt lesbar (Migration in `docs/DATENFORMATE.md`).
- Fehlerstatus: Sprecherfehler → Transkript erhalten, Exitcode 4, gezielte
  Wiederholung nur der Sprechertrennung (ASR-Cache); `--voll` macht aus
  unvollständiger Verarbeitung keinen Erfolg.
- Wiederaufnahme für Kern, reine Transkription und Vollkette (Instrumentierung
  `schritte` in `run.json`); Modellrevisionen und eindeutige Interview-IDs;
  fremde Locks bleiben erhalten; manuelle Änderungen werden nach `.bak` gesichert.
- Nutzerselbsttest mit echtem Sprachclip (`tests/data/sprachclip.wav`,
  selbst erzeugt, 2 Stimmen); Mock-Tests bleiben reine Entwicklungstests.
- 39 pytest-Prüfungen (darunter gemeinsame Merge-Regression mit diar2-Logik).

## 0.2.0 (2026-10-13, nicht abgenommen)

- Kern + regelbasierte Erweiterung, Mock-Selbsttest, Platzhalter-Installer
  (`Install-Runtime` schrieb nur einen Marker). Durch 0.3.0 ersetzt.
