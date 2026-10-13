# Sicherheit (SECURITY)

## Geltung

Dieses Werkzeug verarbeitet sensible Interviewaufnahmen lokal. Sicherheits-
hinweise betreffen daher vor allem den Umgang mit Daten, nicht nur Code.

## Vertrauliches melden

Sicherheitslücken (z. B. Übertragung von Aufnahmeinhalten, Token in Logs,
Ausführung über Dateinamen) bitte nicht öffentlich als Issue melden, sondern
direkt an den Projektbetreuer (Adresse nach Repositoryerstellung hier
eintragen). Antwort wird innerhalb von 14 Tagen angestrebt.

## Was Nutzerinnen und Nutzer beachten sollten

- Das Hugging-Face-Token (nur für den freigabepflichtigen Erst-Download)
  wird nie gespeichert und gehört in keine Logs, Screenshots oder Issues.
- `oh-diagnose` gibt keine Aufnahmeinhalte oder Zugangsdaten aus; vor dem
  Teilen einer Diagnoseausgabe trotzdem kurz prüfen.
- Windows-Warnungen beim ersten Start stammen aus der fehlenden
  Code-Signatur (erwartet, siehe `docs/TESTBERICHT.md`); Schutzfunktionen
  nicht pauschal abschalten.
- Unterstützte Versionen: nur die jeweils neueste freigegebene Version
  erhält Korrekturen (Vorabversionen nach bester Möglichkeit).
