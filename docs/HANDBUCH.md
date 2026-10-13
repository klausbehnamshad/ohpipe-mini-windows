# ohpipe-mini Windows — Handbuch (v0.3.2, deutsch)

## 1. Was das Paket tut
Lokale Transkription mit Sprechertrennung (SPK_01, SPK_02, …) auf dem eigenen
Rechner. Keine Aufnahme, kein Transkript geht an einen Cloud-Dienst.
**Neuimplementierung** mit FFmpeg + faster-whisper (CPU/INT8) + pyannote lokal —
keine exakte Portierung der Mac-Methode (MLX/Nemotron laufen auf Windows x64
nicht). Die Sprecherzuordnung arbeitet auf Wortebene mit echten Wortzeiten
(Faustregeln aus diar2, Commit `4ea28ce`); kurze Einwürfe bleiben beim
Einwerfer, Antworten nach Fragen bekommen einen eigenen Beitrag.
Abweichung zum Mac: `oh-kette DATEI` verarbeitet standardmäßig nur den
Kern; `oh-kette DATEI --voll` führt zusätzlich die Interviewkette aus. So braucht
bloßes Transkribieren keine Metadatenumgebung.

## 2. Voraussetzungen
Windows 11 Home 24H2, x64, CPU-Profil zuerst. Andere Architekturen: nur x64
unterstützt (ARM64 nicht getestet, nicht versprochen). Kein Admin, kein WSL,
kein Docker, kein Git, kein Visual Studio nötig. Kein manuell gepflegtes
System-Python nötig (privates Python in `runtime\`).

## 3. Einrichtung
Siehe START-HIER.txt. Setup erkennt Hardware (CPU/RAM/Grafik), prüft ca. 12 GB
frei, richtet die private Laufzeit ein, lädt Modelle transparent (Größe,
Speicher, Bedingungen), schreibt Revisionen nach `runtime\state.json`.
Zweiter Setup-Lauf beschädigt nichts. Updates nur ausdrücklich; Nutzerdaten
bleiben; Rückkehr zur Vorversion vorgesehen.

## 4. Erster Befehl
`oh-kette "C:\…\Interview.mp4"` — Schritte und Warnungen im Terminal, am Ende
der Ergebnisordner. Pfade mit Leerzeichen, Umlauten, `&`, Apostroph, Klammern
werden als Argumente übergeben (keine Shell-Auswertung). Nach Setup läuft die
Verarbeitung **offline**; fehlende Modelle brechen mit Einrichtungshinweis ab,
statt unbemerkt nachzuladen.

## 5. Ergebnisse
`%USERPROFILE%\Downloads\ohpipe-mini\diar2\output\NAME\` (NAME mit
Inhalts-Hash, eindeutig je Datei): TXT (lesbar, Zeit + Sprecher, Einwürfe in
Klammern), SRT (gültig, geordnet, Sprecher sichtbar), JSON Format 2
(versioniert: IDs, Start/Ende, Text, Sprecher, Wörter mit Zeitquelle,
Sätze, Turns, Prüfhinweise, Sprache, Rollenvorschlag, Tech-Metadaten; Rollen
getrennt, Status `unbestaetigt`), RTTM (Sprecherintervalle zum Austausch),
Hörliste (Prüfstellen mit Grund + 60-s-Rollenkontrolle), `run.json`
(Input-SHA256, Version, Modellrevisionen, Parameter, Verarbeitungsschritte;
keine Tokens, möglichst kein Transkriptinhalt in Logs). Jedes Wort trägt
`time_source` (`faster-whisper` gemessen oder `geschaetzt-segment` beim
gekennzeichneten Rückfall). Exitcodes: 0 fertig, 2 Fehler, 3 Eingabe bereits
in Verarbeitung, 4 Transkript erhalten aber Sprechertrennung fehlgeschlagen
(Status `teilweise (diarisierung-fehlgeschlagen)`; erneuter Lauf wiederholt
nur die Sprechertrennung; `--voll` entfällt dann). `--nur-transkript` ist
Absicht (Status `teilweise (nur-transkript)`) und erscheint nie als
„vollständig“.

## 6. Formate und Spuren
Ziel: WAV MP3 M4A AAC FLAC OGG Opus WMA AIFF; MP4 MOV MKV AVI WebM M4V WMV.
Inhalt wird geprüft (kein Vertrauen auf Endungen); fehlende Audiospur,
DRM, leere/beschädigte Dateien melden sich verständlich. Mehrere Spuren:
Anzeige + `--spur N` (niemals stille leere Spur). Getestete Kombinationen:
siehe TESTBERICHT (derzeit WAV-Selbsttest mit echter Verarbeitung auf Mac;
Windows-Abnahme ausstehend).

## 7. Profile und Sprachen
`--profil klein|standard|qualitaet` (klein für knappen RAM; Standard = CPU).
Modelle werden nacheinander geladen; GPU-Fehler fallen auf CPU zurück.
Standard: Originalsprache; `--sprache de|en|fr|auto` (manuelle Wahl + Auto).
Luxemburgisch/gemischt: nur nach tatsächlicher Prüfung als unterstützt
bezeichnen (derzeit offen).

## 8. Stapel, Hörkontrolle, Wiederaufnahme
`oh-stapel` (Standard: Eingabeordner, nicht rekursiv; `--rekursiv` opt-in;
eine defekte Datei stoppt andere nicht; Schlussbilanz mit Pfaden).
`oh-hoer NAME` (nummerierte Prüfstellen, längste zuerst; erste Minute zur
Rollenkontrolle prüfen), `oh-hoer NAME 5` (~15 s lokal, Anfang/Ende begrenzt,
auch für Video-Eingaben). Wiederaufnahme: unveränderter Zweitlauf (Input-ID +
Parameter + Modellrevisionen + konsistente Ausgaben) startet keine Inferenz
neu; `--neu` rechnet bewusst neu; manuelle Korrekturen werden nicht
überschrieben; atomare Writes; Lock gegen Doppelläufe; Strg+C erhält fertige
Schritte.

## 9. Erweiterung (enthalten ab v0.2.0, regelbasiert ohne Sprachmodell)
Reihenfolge bei `--voll`: Transkript mit Sprechern, IMM-Entwurf, lokale
Vorschläge, Prüfung personenbezogener Hinweise, Prüfliste. Vorschläge entstehen
durch Regeln aus dem Transkript (kein Ollama/LLM nötig, keine Cloud) und bleiben
von bestätigten Daten getrennt. Dateinamen folgen diar2meta:
`diar2meta/output/NAME/NAME.imm.draft.json` (Entwurf),
`NAME.imm.provenance.json` (Herkunft je Wert), `NAME.entwurf.json` (drei Titel,
Abstract mit 2–3 Sätzen, 6–10 Schlagwörter, Segmentnamen),
`NAME.pii.json`, `NAME.pruefliste.txt`. Fixiertes Schema: IMM-Core 1.1.0
(offline geprüft, keine entfernten Referenzen).

- `oh-rollen NAME --tausch`: bestätigte Vertauschung bei genau zwei
  Stimmen — tauscht nur die Rollen fragend/interviewt (keine Modelle);
  Sprecherkennungen, Wörter, Turns und Exporte bleiben stabil. Sonst
  `--setzt fragend=SPK_01 interviewt=SPK_02` (Form `ROLLE=SPK_xx`;
  Rollen: fragend, interviewt, dritte; unbekannte Rollen, Duplikate und
  falsche Sprecher werden abgewiesen). Sichert nach `.bak`, markiert
  abhängige Vorschläge als veraltet. Rollen bleiben bis zur Bestätigung
  `unbestaetigt`.
- `oh-pruefen NAME`: sucht u. a. Namen nach Herr/Frau, Adressen, E-Mail,
  Telefonnummern sowie Auffälligkeiten aus Transkript und Dateiname; Treffer mit
  Fundstelle. Keine garantierte Anonymisierung.
- `oh-entwurf NAME [--neu] [--nur titel|abstract|keywords|labels]`: Vorschläge
  kontrolliert (neu) erstellen oder feldweise bearbeiten.
- `oh-uebernehmen NAME FELDER... [--titel-nr 2]`: sichert den Entwurf (`.bak`),
  übernimmt gewählte Vorschläge, validiert danach.
- `oh-l1 NAME [--nur-fragen] [--codebuch PFAD] [--neu]`: Fragenleitfaden mit
  Zeitmarken; je Sprechersegment ein Rohcode mit wörtlichem Beleg (Segmente unter
  vier Wörtern: `KURZ`); Verdichtung auf 8–15 Kategorien; Häufigkeiten und Anteil
  verankerter Belege. `--codebuch` codiert geschlossen mit dessen Kategorien.
  Codebuch-Vorschlag (`ohpipe.l1.codebook.v1`) mit offenen Definitionen bereitet
  die menschliche Prüfung vor und ersetzt sie nicht.
- `oh-bericht [--ausgabe status.md]`, `imm-todo`, `imm-check DATEI` (offline),
  `imm-schema-sync` (nur auf Aufruf online, ändert keine Dateien).
`consent_status` und `accessRights` setzt der Nutzer aus der Einwilligung; sie
werden nie aus dem Gespräch erfunden. OHPIPE-Übergabe bleibt ein manueller
Schritt ohne Schreiben in fremde Checkouts.
`oh-status` zeigt die OHPIPE-Bindung nur bei Einrichtung; `oh-diagnose` ohne
Inhalte/Token.

## 10. Häufige Fehler und Deinstallation
Volle Platte, gesperrte Ausgabe, reservierte Namen (CON/PRN/AUX/NUL/COM1…),
gleichnamige Eingaben: kontrollierte Meldungen, keine Stilllegung anderer
Dateien. Deinstallation: `scripts\Uninstall.ps1` (Programm weg; Aufnahmen/
Ergebnisse/Modelle bleiben, außer `-MitDaten`). Uns signierter Build: Windows-
Warnung erklärt (Herkunft), kein Abschalten von Schutzfunktionen.
