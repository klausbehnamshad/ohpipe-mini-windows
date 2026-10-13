# Datenschutz (ohpipe-mini-windows 0.3.0)

## Grundsatz

Aufnahmen und Transkripte werden auf dem eigenen Rechner verarbeitet. Das
Programm sendet keine Audio-, Transkript- oder Modelldaten an Cloud-Dienste,
schaltet Telemetrie der eingebundenen Bibliotheken ab und bindet lokale
Dienste nur an die eigene Maschine. Das ersetzt weder Einwilligung noch eine
projektbezogene Entscheidung über Zugang und Veröffentlichung; eine pauschale
DSGVO-Konformität wird nicht behauptet.

## Dateien und Orte

- **Eingaben:** bleiben, wo sie liegen (nur gelesen).
- **Ergebnisse:** `%USERPROFILE%\Downloads\ohpipe-mini` (frei wählbar über
  Umgebungsvariable `OHPIPE_DATA`). Vorsicht bei synchronisierten Ordnern
  (OneDrive u. ä.): Deren Dienst überträgt Dateien — für Interviews einen
  lokalen Ordner wählen.
- **Arbeitskopien:** `diar2/.work/NAME/` (16-kHz-Arbeits-WAV, ASR-Cache,
  Merge-Arbeitsdateien). Keine Originale darin.
- **Modelle:** `Downloads\ohpipe-mini\modelle` + Hugging-Face-Cache des
  Setup-Kontos (nur Gewichte, keine Aufnahmen).
- **Protokolle:** `NAME.run.json` nennt Eingabe-Hash, Versionen, Parameter
  (keine Tokens, möglichst keine Transkriptinhalte in Technik-Logs).
- **Löschung:** `scripts\Uninstall.ps1` entfernt Programmteile; Aufnahmen,
  Ergebnisse und Modelle nur mit ausdrücklich gewählter Löschoption.
  Temporärdateien werden gezielt aufgeräumt, Originale nie gelöscht.

## Netzwerk

- **Einrichtung:** braucht einmalig Internet (Laufzeit, Pakete, Decoder,
  Modelle, ggf. Modellfreigabe mit Token).
- **Verarbeitung:** soll offline funktionieren; es wird nichts unbemerkt
  nachgeladen. Ein Lauf mit vollständig gesperrtem Netz ist noch nicht
  geprüft (offen, siehe Testbericht).
- **Ausdrücklich online:** nur Updates und `imm-schema-sync` (jeweils nur
  auf Aufruf, ändern lokale Dateien nicht von selbst).

## Token und Freigaben

Der Hugging-Face-Token gilt nur für den freigabepflichtigen Erst-Download
der Sprechertrennung, wird unsichtbar abgefragt und nie gespeichert
(`token_gespeichert: false` in `runtime/state.json`). Danach ist kein Token
nötig. Die Prüfung personenbezogener Hinweise (`oh-pruefen`) ist eine
Unterstützung, keine garantierte Anonymisierung.
