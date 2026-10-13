# Testbericht v0.3.2 (Mac-Entwicklung, 13.10.2026 — KEINE Windows-Abnahme)

Build: 0.3.2, Paket `ohpipe-mini-windows-0.3.2.zip` (SHA256 in der
beiliegenden `.sha256`-Datei, nicht hier — der Bericht steht selbst im
Paket). Entpacktest: `ohpipe.py status` läuft aus dem ZIP (Version 0.3.2).
Entwicklungsrechner: Mac, Python 3.13, FFmpeg 8.1.1, pytest.

## Neu in 0.3.2 (Nacharbeiten, ohne Windows-Abnahme)

- Doppelte Rollen in `--setzt` werden abgewiesen (Regressionstest);
  39 pytest-Prüfungen (Rollen/Isolation jetzt 8).
- Windows-CI installiert die Testvoraussetzungen reproduzierbar aus dem
  Hash-Lock (gleiches Kommando wie im Setup). PowerShell-Parserlauf
  selbst steht weiter aus (kein Interpreter auf dem Entwicklungsrechner).
- Isolation, Rollenkette und Erweiterung weiter bestanden (38er-Stand
  aus 0.3.1 unverändert gültig).

## Neu in 0.3.1 (Prüfbericht-Korrekturen, ohne Windows-Abnahme)

- PowerShell `${Komponente}`-Syntax an beiden Stellen korrigiert; alle
  `.ps1`-Dateien auf `$Variable:`-Muster auditiert (nur legitime `$env:`
  übrig); CI prüft künftig alle `.ps1` per Parser plus Muster plus `.cmd`.
  (Kein PowerShell-Interpreter auf dem Entwicklungsrechner; Parsercheck
  läuft in Windows-CI.)
- Isolierter Start (`python -I`, wie Windows-Embed): Anwendungsordner fest
  in `app/ohpipe.py` eingebunden plus `._pth`-Eintrag im Setup; Regression
  mit `entwurf --help` und `diagnose` unter `-I` ohne Arbeitsverzeichnis.
- Rollenkorrektur: `--setzt` parst/validiert `ROLLE=SPK_xx` (unbekannte
  Rollen, Duplikate, falsche Sprecher, fehlende Werte → Exit 2);
  `--tausch` ändert nur Rollen (bestehende tauschen, sonst erste Stimme =
  interviewt), Sprecher/Wörter/Turns/Exporte bleiben stabil (mit `.bak`
  und Veraltet-Markierung). Alte Tausch-Semantik (Sprecherlabels
  vertauschen) war falsch und ist ersetzt; alter Test beanspruchte nur
  Exitcode/Status und gilt weiter.
- OneDrive-Hinweis im Setup (Warnung bei synchronisiertem Datenordner,
  sonst Merkhinweis); `.gitignore` liegt neu im Paket (Repo-Vorlage).
- Sprachmodellerweiterung bleibt regelbasiert und damit offen — in
  Releasebeschreibung und OFFENE-PUNKTE.md ausdrücklich so benannt.

## Bestanden (seit 0.3.0, weiter gültig)

- 39 pytest-Prüfungen: Export/JSON/Namen (5), Erweiterung (6),
  Wiederaufnahme/Fehlerstatus/Lock/ID/Cache/Modellwechsel/Konkurrenz (12),
  Mock-Ablauf (1), Merge-Regression (7), isolierter Start/Rollen (8),
  gemeinsame Merge-Regression (7).
- Echte Transkription: faster-whisper 1.1.0, tiny-Modell @ Revision
  `d90ca5fe` (wie in `models.json`), CPU/INT8, offline (`HF_HUB_OFFLINE=1`),
  33-s-Testclip: Sprache Deutsch (Wahrscheinlichkeit 1,0), 9 Segmente,
  Schlüsselwörter 4/8 (Fehler z. B. „Bauernhof nebenan“ → „Bauern hoffen“,
  „Nachbarort“ → „Barort“).
- Echte Sprechertrennung: pyannote-3.1 @ Revision `84fd2591` (wie in
  `models.json`), CPU: Pipeline-Ladung 7,1 s, Diarisierung 14,1 s,
  alle 8 Testbeiträge der richtigen Stimme zugeordnet (2 Sprecher).
- Merge-Äquivalenz: Adapter-RTTM byte-identisch zum diar2-Referenz-RTTM
  bei identischen Eingaben (Test).
- Lock-Prüfung: 97 hash-geprüfte Wheels ohne Duplikate; `docopt`-Wheel im
  Paket stimmt mit Lock-Hash überein; FFmpeg-ZIP (110 MB) gegen
  Publisher-Prüfsumme verifiziert, alle ZIP-CRCs ok.
- Selbsttest-Pfade: `selbsttest_echt.py` meldet fehlendes Setup korrekt
  mit Exitcode 2 statt abzustürzen.
- Gefundene und behobene Fremdfehler: av>=19 bricht faster-whisper 1.1.0
  (Lock capped auf 15.1.0), huggingface-hub>=1.0 bricht pyannote 3.3.2
  (Lock capped auf 0.34.4, Download damit nachgewiesen), torchaudio>=2.9
  passt nicht zu torch 2.3.1 (Lock auf 2.3.1), Pipeline braucht lokale
  `config.yaml` (Code korrigiert).

## Offen (nicht als bestanden melden)

Windows-11-Abnahme komplett (Setup, PS 5.1/7, CPU, echte Formate, Qualität
gegen Referenz, Sprachen, Stille/Musik, Langlauf, Offline mit gesperrtem
Netz, Stapel-mix, Deinstallation), 5-Minuten-Referenz (WER/DER),
öffentlicher Download, Signatur. Referenzdaten: nur synthetischer Clip,
keine privaten Interviews. Echte ASR/Diarisierung liefen auf keinem
Windows-System.
