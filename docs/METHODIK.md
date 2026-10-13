# Methodik (ohpipe-mini-windows 0.3.0)

## Arbeitsschritte

1. **Import:** FFmpeg prüft den Dateiinhalt (nicht nur die Endung) und wandelt
   die gewählte Tonspur in 16 kHz Mono um. Originale bleiben unverändert.
2. **Automatische Textgewinnung:** faster-whisper (CPU) erkennt Sprache und
   Text, mit echten Wortzeiten (`word_timestamps`) je Wort.
3. **Sprecherintervalle:** pyannote-3.1 (lokal, feste Revision) liefert
   Zeitspannen je Stimme (`SPK_01`, …) innerhalb dieser Aufnahme.
4. **Zusammenführung:** `diar2_merge` (aus diar2, Commit `4ea28ce`,
   unverändert übernommen) ordnet jedes Wort einer Stimme zu (Wortmitte im
   Intervall, sonst größte Überlappung im Toleranzfenster 0,5 s), fasst Wörter
   zu Sätzen zusammen (Satzzeichen oder Pause über 1,5 s), glättet und teilt
   unpunktuierte Sprecherwechsel im Satz.
5. **Hörprüfung:** Prüfstellen mit Grund (Wechsel im Satz, sehr kurzer Turn,
   Überlappung), dazu immer die Kontrolle der ersten 60 Sekunden.
6. **Menschliche Bestätigung:** Rollen (`fragend`/`interviewt`) gelten bis zur
   Bestätigung mit `oh-rollen` als unbestätigt; Korrekturen sichert das
   Programm vor Neuberechnung.

## Einwürfe: „Mhm“ und „Ja“

Ein „Mhm“ von höchstens zwei Wörtern und 1,2 Sekunden Dauer während der
andere spricht bleibt ein *Einwurf* bei der eigenen Stimme und bekommt keinen
eigenen Redebeitrag. Ein bestätigtes „Ja“ direkt nach einer Frage des anderen
ist dagegen eine *Kurzantwort*: Sie bildet einen eigenen kurzen Beitrag und
verschwindet nicht als entbehrlicher Einwurf. Steht nach ihr derselbe Sprecher
weiter, bleibt sie trotzdem als Antwort sichtbar. Alle Schwellen stehen in
`app/diar2_merge.py` (Modulkonstanten) und gelten unverändert wie in diar2.

## Beziehung zu diar2 und Windows-Unterschiede

Fachliche Regeln (Wortzuordnung, Glättung, Einwürfe, Hörliste, RTTM-Export)
stammen aus diar2 (Mac, Apple Silicon). Auf Windows laufen andere Modelle:
faster-whisper statt mlx-whisper (Wortzeiten direkt aus der Erkennung statt
WhisperX-Nachausrichtung), pyannote-3.1 statt Nemotron (eine statt zwei
Meinungen — ohne Zweitmeinung gibt es keinen Modellvergleich). Die gemeinsame
Regression (`tests/test_merge_gemeinsam.py`) weist nach, dass identische
Wortdaten auf beiden Wegen zu denselben Entscheidungen führen; das ist kein
Beweis gleicher Erkennungsqualität.

## Zeitquellen und Kennzeichnung

Jedes Wort trägt `time_source`: `faster-whisper` (gemessen) oder
`geschaetzt-segment` (Rückfall: proportional auf die Segmentspanne gelegt,
wenn die Erkennung keine Wortzeiten lieferte). Geschätzte Zeiten erscheinen
nie als gemessene; der Rückfall steht in `alignment` (`segment-fallback`),
in der JSON und im Laufprotokoll. Wortzeiten nur aufnehmen, wenn sie
tatsächlich berechnet wurden.

## Reichweite

Das Werkzeug erstellt einen durchsuchbaren, zeitmarkierten Arbeitsentwurf mit
Stimmenlabels. Es erstellt keine gesprächsanalytische Feintranskription:
Pausenzeichen, Dehnungen, Abbrüche und exakte Überlappungsnotation entstehen
nicht automatisch. Sprecherlabels sind innerhalb einer Aufnahme stabil;
dieselbe Person über mehrere Interviews hinweg zu erkennen ist nicht
vorgesehen. Personennamen werden nie erraten.
