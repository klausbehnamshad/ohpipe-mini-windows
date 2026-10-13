# Datenformate (ohpipe-mini-windows, JSON-Format 2)

Ergebnisordner: `%USERPROFILE%\Downloads\ohpipe-mini\diar2\output\NAME\`
(`NAME` = Dateistamm + kurzer Inhalts-Hash, z. B. `Interview--9e2c610d`).
Folgebefehle (`oh-hoer`, `oh-rollen`, …) nutzen genau diesen Namen.

## Dateien

| Datei | Inhalt | Wofür |
|---|---|---|
| `NAME.txt` | Lesbar, Zeit + Sprecher, Einwürfe in Klammern | menschliche Prüfung |
| `NAME.srt` | Gültige Untertitel, zeitlich geordnet, Sprecher sichtbar | Untertitel |
| `NAME.json` | Versioniert (s. u.), Segmente, Wörter, Sätze, Turns, Rollen, Herkunft | Weiterverarbeitung |
| `NAME.rttm` | Geglättete Sprecherintervalle (`SPEAKER NAME 1 start dauer … SPK_xx`) | Austausch/Auswertung |
| `NAME.hoerliste.txt` | Prüfstellen mit Grund + 60-s-Rollenkontrolle | Hörprüfung |
| `NAME.run.json` | Eingabe (SHA256), Version, Modellrevisionen, Parameter, Schritte | Nachvollzug |

## JSON-Format 2 (aktuell)

```json
{
  "format": "ohpipe-mini-windows", "format_version": 2, "name": "…",
  "language": "de", "roles": {}, "role_status": "unbestaetigt",
  "segments": [{"id": "seg0001", "start": 0.0, "end": 5.3,
                "text": "…", "speaker": "SPK_02", "flags": []}],
  "words": [{"i": 0, "text": "Guten", "start": 0.0, "end": 0.4, "score": 0.9,
             "timed": true, "time_source": "faster-whisper",
             "speaker": "SPK_02", "speaker_raw": "SPK_02",
             "overlap": false, "overlap_speakers": [], "einwurf": false,
             "second_opinion": null, "sentence": 0}],
  "sentences": [{"i": 0, "start": 0.0, "end": 5.3, "speaker": "SPK_02",
                 "text": "…", "sprecherwechsel_im_satz": false,
                 "kurzantwort": false}],
  "turns": [{"speaker": "SPK_02", "start": 0.0, "end": 5.3,
             "sentences": [0], "einwuerfe": []}],
  "alignment": "faster-whisper",
  "merge": {"tool": "diar2-merge 0.1.0",
            "quelle": "diar2@4ea28ce9736a4de56584c325533c653b1b8e4951",
            "schwellen": {}},
  "rollenvorschlag": {"erste_stimme": "SPK_02", "vorschlag": "fragend",
                      "status": "unbestaetigt-vorschlag", "hinweis": "…"},
  "tech": {"app": "0.3.0", "profil": "standard", "asr_model": "base", "…": "…"}
}
```

- `speaker`/`SPK_xx`: Stimme innerhalb dieser Aufnahme, keine Person.
- `roles`/`role_status`: getrennt bestätigt (`oh-rollen`), nie vom Modell.
- `rollenvorschlag`: höchstens ein Vorschlag für die erste Stimme, immer
  unbestätigt; kein Rollenpaar bei drei oder mehr Stimmen.
- `time_source`: `faster-whisper` (gemessen) oder `geschaetzt-segment`
  (Rückfall, siehe `alignment: segment-fallback` + `alignment_hinweis`).
- `flags` an Segmenten: `pruefen:…` (anschauen) vs. `heuristik:…`
  (Faustregel, ausdrücklich markiert). Erfundene Konfidenzwerte gibt es nicht.
- Manuelle Änderungen: Vor jeder Neuberechnung sichert das Programm die
  bisherigen Dateien nach `NAME.*.bak`; `oh-rollen` sichert ebenfalls.

## Zuordnung diar2 ↔ Windows

| diar2 (`*.diar2.*`) | Windows | Anmerkung |
|---|---|---|
| Wortliste (`words`) | `words` in `NAME.json` | gleiche Struktur, `time_source` zusätzlich `faster-whisper`/`geschaetzt-segment` |
| Sätze (`sentences`) | `sentences` + `segments` | Windows-Segmente entsprechen Merge-Sätzen (mit `flags`) |
| Turns + Einwürfe | `turns` in `NAME.json` | gleiche Struktur |
| Hörliste (`art`, `start`, `end`, `text`) | `NAME.hoerliste.txt` + Gründe | Entscheidungen identisch, Datei im Windows-Stil |
| `*.diar2.rttm` (geglättet) | `NAME.rttm` | gleiches Format, Aufnahme-ID = Interviewname |
| `*.diar2.txt` / `*.diar2.srt` | `NAME.txt` / `NAME.srt` | Windows-Renderer (Turn-Einwürfe in Klammern, Satz-Cues) |
| `second_opinion` | immer `null`/falsch | nur ein Diarisierungsmodell — kein Vergleich erfunden |
| Namen (`Interviewer,…`) | `SPK_xx` + `rollenvorschlag` | keine Modell-Identifikation, Rollen nur von Hand |

## Migration Format 1 → 2

Format 1 (`format_version: 1`, Segmente ohne `words`, Stand 0.2.0) bleibt
lesbar: Wiederaufnahme, Hörkontrolle, Rollen, Stapel und Erweiterung arbeiten
mit Segmenten weiter. Eine Neuberechnung (`--neu` oder geänderte Parameter/
Modelle) erzeugt Format 2; dabei sichert das Programm die alten Dateien nach
`.bak`. Alte Modelle oder Parameter erscheinen durch die neue Herkunftsangabe
nicht rückwirkend als verwendet: `run.json` nennt die tatsächlich genutzte
Revision je Lauf. Eine automatische Umschreibung alter Ergebnisordner findet
nicht statt.
