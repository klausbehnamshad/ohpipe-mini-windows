# Selbsttest-Clip `sprachclip.wav` (32,8 s, 16 kHz Mono, ca. 1 MB)

Fiktives deutsches Zwei-Personen-Gespraech, selbst erzeugt am 2026-10-13 mit
Piper-TTS (MIT-Lizenz, offline) aus frei verfuegbaren Stimmen:

- Interviewerin (weiblich): `de_DE-eva_k-x_low` (M-AILABS-Datensatz, offen)
- Erzaehler (maennlich): `de_DE-thorsten-medium` (Thorsten-Voice, CC0)

Quelle der Stimmmodelle: https://huggingface.co/rhasspy/piper-voices
Nur diese erzeugte WAV liegt bei (keine Stimm- oder ASR-Modellgewichte).

Gesprochene Saetze (Referenz, Wortlaut der Synthese-Eingabe):

1. (F) Guten Tag und herzlich willkommen zu unserem Gespräch über das Leben auf dem Dorf.
2. (M) Guten Tag. Ich bin im Norden in einem kleinen Dorf aufgewachsen, mit einem Bauernhof nebenan.
3. (F) Wie war die Schule damals für Sie im Nachbarort?
4. (M) Die Schule war streng. Wir sind jeden Morgen zu Fuß gegangen, bei Wind und Wetter.
5. (F) Was haben Sie nach der Schule gemacht?
6. (M) Ich habe eine Lehre gemacht und später in der Fabrik am Stadtrand gearbeitet.
7. (F) Vielen Dank für das Gespräch und Ihre Erinnerungen.
8. (M) Sehr gerne. Auf Wiederhören.

Zwischen den Beitraegen je 0,5 s Stille. Keine echten Personen, keine
personenbezogenen Daten. Erwartung im Nutzerselbsttest (`tests/selbsttest_echt.py`):
Status `fertig`, mindestens 4 Segmente, mindestens 2 verschiedene Sprecher,
Schluesselwoerter (drei aus: dorf, schule, fabrik, gespraech, lehre, bauernhof,
stadtrand, erinnerungen) im Transkript.
