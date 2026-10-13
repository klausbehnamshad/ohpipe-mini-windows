# Herkunft von `app/diar2_merge.py`

- Quelle: `diar2_merge.py` aus dem lokalen Repository `diar2-muse`
  (gehoert zu [klausbehnamshad/diar2](https://github.com/klausbehnamshad/diar2)).
- Fixierte Revision: Commit `4ea28ce9736a4de56584c325533c653b1b8e4951`
  vom 2026-10-04 („SRT schreibt jeden Cue als Name Doppelpunkt Text“).
- SHA256 der Quelldatei: `cd2cfff86c4bc0e0dd960804c8b628ca9a5c2e9722267b4035ec80dd72ca9fd7`
- Lizenz: Apache-2.0 (Hinweis in Datei und `LICENSE` behalten).
- Lokale Anpassung: nur dieser Herkunftskopf als Kommentar; die Logik
  (Schwellen, Glättung, Einwurfregeln, Hörliste) ist unverändert.
- Aufrufkonvention auf Windows (`app/diar_adapter.py`): immer
  `names_opt="-"`, damit automatische Kennungen `SPK_xx` erhalten bleiben.
  Gesprächsrollen (`fragend`/`interviewt`) werden ausschließlich von Hand
  über `oh-rollen` bestätigt; das Modul liefert höchstens einen
  Rollenvorschlag für die zuerst sprechende Stimme.
- Grenzen der übernommenen Logik: für Zwei-Personen-Interviews auf dem Mac
  entwickelt; auf Windows laufen andere Modelle (faster-whisper statt
  mlx-whisper, pyannote 3.1 statt Nemotron). Die Regression
  (`tests/test_merge_gemeinsam.py`) prüft identische Entscheidungen bei
  identischen Wortdaten — kein Beweis identischer Erkennungsqualität.
- Keine Zweitmeinung auf Windows (nur ein Diarisierungsmodell):
  `second_opinion` ist immer falsch; es werden keine nicht berechneten
  Modellvergleiche angezeigt.
