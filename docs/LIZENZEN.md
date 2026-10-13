# Lizenzen und Weitergabe (Stand v0.3.0)

Der eigene Projektcode (`app/ohpipe.py`, `app/diar_adapter.py`, `bin/`,
`scripts/`, Tests, Dokumentation) steht unter **Apache-2.0** (siehe
`LICENSE`) — passend zur Hauptquelle diar2, die ebenfalls Apache-2.0 ist.
`app/diar2_merge.py` ist aus diar2 übernommen (Commit `4ea28ce`,
Herkunft `app/diar2_HERKUNFT.md`), Lizenz- und Herkunftshinweise bleiben
erhalten.

| Bestandteil | Lizenz / Bedingung | Weitergabe |
|---|---|---|
| Eigener Code | Apache-2.0 | frei |
| diar2-Merge-Modul | Apache-2.0 (Quelle genannt) | frei |
| faster-whisper (Code) | MIT | nennen |
| pyannote.audio (Code) | MIT | nennen |
| Systran faster-whisper-Modelle (tiny/base/small) | offen (CC-BY-ähnlich, Modellkarte beachten) | Setup lädt transparent mit Revision |
| pyannote speaker-diarization-3.1 / segmentation-3.0 | **freigabepflichtig** (Bedingungen auf der Modellseite bestätigen, Token nur für Erst-Download, nie gespeichert) | **nicht** mitliefern; Setup lädt transparent; danach kein Token nötig |
| FFmpeg 8.1.2 (gyan essentials, statisch) | **GPLv3** (nur `ffmpeg.exe`/`ffprobe.exe` genutzt) | als Setup-Download mit Prüfsumme; bei privater Weitergabe zulässig, Quellenverweis liegt bei |
| Python 3.12.10 embeddable | PSF-Lizenz | Setup-Download mit Prüfsumme, nennen |
| Testclip `sprachclip.wav` | selbst erzeugt (Piper-TTS, MIT; Stimmen: Thorsten-Voice CC0, M-AILABS offen) | liegt bei, frei |
| docopt-Wheel in `vendor/wheels` | MIT (reines Python) | liegt bei |

Keine Telemetrie: HF/pyannote-Umgebungsabschaltung im Code, keine
Absturzberichte mit Inhalten, lokale Dienste nur an Loopback. Signatur nur
behaupten, wenn der Build tatsächlich signiert ist (derzeit nicht).
