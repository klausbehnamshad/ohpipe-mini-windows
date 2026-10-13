# Offene Punkte und Unterschiede (ehrlich, v0.3.0)

## Neuimplementierung, keine exakte Portierung

- Mac: MLX whisper-large-v3-turbo + Nemotron-Diarisierung. Windows:
  faster-whisper (CPU/INT8, echte Wortzeiten) + pyannote-3.1 lokal, mit den
  fachlichen diar2-Regeln (Commit `4ea28ce`, Wortebene, Einwürfe, Hörliste,
  RTTM). Andere Fehlertypen und Qualität; kein Kompatibilitätsversprechen
  für RTTM/Stages-Formate über die dokumentierte Zuordnung hinaus.
- Erweiterung: regelbasierte Neuimplementierung **abgeleitet von diar2meta
  0.1.0** (kein Sprachmodell — kein Mac-Vorbild, keine LLM-Qualität). Das
  lokale Sprachmodell aus dem Bauauftrag bleibt ein offener Auftragsteil;
  Trennung Vorschlag/bestätigt, Sicherung, Belegprüfung und
  Rollenbestätigung gelten unverändert.
- Originalquellen `ohpipe-mini.sh`, `ohm_llm.py`, `ohm_l1.py`,
  `ohm_tools.py`, `governance/2026-001.md` wurden nicht gefunden und bleiben
  offene Abhängigkeiten für einen exakten Abgleich. Keine IMM-Felder oder
  OHPIPE-Schnittstellen erfunden.
- Fixiertes Schema: IMM-Core **1.1.0** (begründet in Vorgängerversion:
  Handbuch nennt 1.1.0; neuere 1.2.0 bewusst nicht gewählt).

## Erledigt in 0.3.1 (Prüfbericht-Korrekturen)

PowerShell-Syntax, isolierter Start (App-Ordner + `._pth`), `--setzt`-Parsing
und `--tausch` als reiner Rollentausch, OneDrive-Hinweis, `.gitignore` im
Paket. Sprachmodellerweiterung bleibt regelbasiert (offen, siehe oben).

## Erledigt seit 0.2.0

Echte Einrichtung (privates Python, Hash-Lock, Decoder, Revisions-Modelle),
Wortebene mit diar2-Logik, RTTM, JSON-Format 2 mit Migration, Fehlerstatus
(Exit 4), Wiederaufnahme (Kern/nur-Transkript/Vollkette), Interview-IDs,
Lock-Schutz, `.bak`-Sicherung, echter Selbsttest-Clip, 39 Prüfungen.

## Noch nicht abgenommen (nicht als fertig ausgeben)

- Windows-11-Home-24H2-Frischsystem: Setup-Lauf, PowerShell 5.1/7,
  CPU-Betrieb, echte Audio-/Video-Beispiele, mehrere Sprecher, lange
  Aufnahme, Wiederaufnahme, gesperrtes Netz — alles offen.
- Formattabelle je Container/Codec mit echten Testdateien (nur WAV auf Mac).
- 5-Minuten-DE-Referenz (WER/DER/Zeit), EN/FR-Clips, 1/2/3-Sprecher-Läufe an
  echten Aufnahmen, Stille/Musik, 1-Stunden-Lauf, Batch-mix.
- Öffentlicher Download und Code-Signatur: separate Distributionsaufgaben,
  für private Weitergabe nicht zwingend (Datei + Prüfsumme genügen).
- GPU-Beschleunigung (optional), ARM64 (nicht versprochen).
