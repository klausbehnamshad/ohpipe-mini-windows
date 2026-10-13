# Qualität (ohpipe-mini-windows 0.3.0)

## Drei Ebenen

1. **Programmlogik** (39 pytest-Prüfungen, ohne Modelle, auf dem
   Entwicklungsrechner bestanden): Exporte, Namen, Wiederaufnahme,
   Fehlerstatus, Locks, Wortzusammenführung (Einwurf vs. Antwort,
   Wechsel im Satz, Überlappung, fehlende Wortzeiten, drei Stimmen).
2. **Echte Modellläufe** (einmalig, Entwicklungsrechner Mac, CPU):
   faster-whisper tiny (festgezurrte Revision, offline) + pyannote-3.1
   (festgezurrte Revision) am selbst erzeugten 33-s-Clip (zwei synthetische
   Stimmen): Sprache Deutsch (Wahrscheinlichkeit 1,0), 9 Segmente, beide
   Stimmen korrekt getrennt (alle 8 Beiträge richtig zugeordnet).
   Wortlaut-Treffer (tiny): „Gespräch“, „Lehre“, „Erinnerungen“ korrekt;
   Fehler z. B. „Bauernhof nebenan“ → „Bauern hoffen“, „Nachbarort“ →
   „Barort“, „Fabrik“ → „Fabriek“. Standardprofil (base) ist genauer,
   wurde hier aber nicht mit Referenzauszählung geprüft.
3. **Prüfung gegen menschliche Referenz** (Wortfehlerrate, Sprecherfehlerrate):
   noch nicht durchgeführt — siehe offene Punkte.

## Begriffe in normaler Sprache

- **Wortfehlerrate (WER):** Anteil falsch erkannter Wörter gegenüber einer
  von Menschen geschriebenen Referenz (kleinere Fehler wie Großschreibung
  zählen je nach Regel mit). Beispiel: 8 Fehler auf 100 Referenzwörter = 8 %.
- **Sprecherfehlerrate (DER-Anteil):** Anteil der Sprechzeit, der der falschen
  Stimme zugeordnet wurde (ohne und mit 0,25-s-Toleranz an Wechseln).
- Beide Maße brauchen eine menschlich erstellte Referenz derselben Aufnahme;
  synthetische Stimmen sind dafür keine repräsentative Stichprobe
  historischer Interviews.

## Datenbasis und Grenzen

- Referenzdaten: nur der selbst erzeugte Clip (`tests/data/sprachclip.wav`,
  Sätze in `sprachclip.README.md`); keine privaten Interviews, keine
  historischen Aufnahmen.
- Laufzeitmessungen (Modellladung, Verarbeitung, RAM, Platte) erfordern
  Zielhardware + Modellprofil + Aufnahmedauer und liegen erst nach der
  Windows-Abnahme vor.
- Ungemessene Tests werden nicht als bestanden gemeldet
  (`docs/TESTBERICHT.md` unterscheidet bestanden/offen).
