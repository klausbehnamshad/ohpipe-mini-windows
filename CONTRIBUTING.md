# Mitwirken (CONTRIBUTING)

Danke fürs Interesse. Das Projekt richtet sich an Forschung und Archive;
Beiträge sind willkommen, brauchen aber keine Softwareentwicklungs-Erfahrung
für Fehlermeldungen.

## Fehlermeldung

Bitte die Vorlage `.github/ISSUE_TEMPLATE/fehlermeldung.md` nutzen: Windows-
Version, Programmversion (`oh-status`), Profil und eine bereinigte
Fehlermeldung. Keine Interviews, Transkripte oder personenbezogenen Inhalte
hochladen — notfalls ein freigegebenes Minimalbeispiel beschreiben.

## Entwicklungsumgebung

- Windows 11 für Abnahme; Entwicklung auch auf anderen Systemen möglich
  (reine Programmlogik ist plattformunabhängig, Modelltests brauchen die
  Hardware).
- Python-Umgebung gehört ins Projekt (`.venv`), nie ins System:
  `python -m venv .venv`, dann darin installieren.
- Prüfungen: `python -m pytest tests/ -q` (29 Prüfungen, ohne Modelle).
  Neue Verhalten brauchen eine fokussierte Prüfung im selben Stil.

## Regeln für Änderungen

- `app/diar2_merge.py` ist aus diar2 übernommen — dort nicht frei
  umschreiben. Windows-Anpassungen gehören in `app/diar_adapter.py`;
  Herkunft und Revision in `app/diar2_HERKUNFT.md` nachführen.
- JSON-Format: Versionskennung erhöhen, Migration testen und in
  `docs/DATENFORMATE.md` beschreiben; alte Ergebnisse und manuelle
  Korrekturen erhalten.
- Keine Erfolgsmeldungen ohne echte Prüfung; keine Qualitätszahlen ohne
  gemessene Referenz; keine Platzhalter als fertig ausgeben.
- Lizenz des eigenen Codes: Apache-2.0. Neue Abhängigkeiten, Modelle und
  deren Bedingungen in `docs/LIZENZEN.md` nachtragen.
