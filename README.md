# ohpipe-mini-windows

ohpipe-mini-windows unterstützt die Vorbereitung von Interviewmaterial für Forschung und Erschließung. Aus einer Audio- oder Videoaufnahme entsteht auf dem eigenen Windows-Rechner ein Transkriptentwurf mit Zeitmarken und Sprecherkennungen. Eine Hörliste hilft, unsichere Stellen in der Aufnahme zu prüfen. Nach der einmaligen Einrichtung beginnt die Verarbeitung mit einem Befehl im Terminal.

> **Stand 0.3.2:** Entwicklungsstand mit echter lokaler Verarbeitung (auf einem Mac-Entwicklungsrechner mit den festgelegten Modellen geprüft, siehe unten). Die Abnahme auf einem frischen Windows-11-Rechner steht aus — bis dahin gilt jede Installation als Vorabversion. Es gibt noch keinen öffentlichen Download. Die Interview-Erweiterung (Titel, Zusammenfassungen, L1) arbeitet regelbasiert; ein lokales Sprachmodell dafür steht aus.

Fachbegriffe in Kürze: *Diarisierung* heißt hier die Zuordnung von Sprachabschnitten zu unterschiedlichen Stimmen (`SPK_01`, `SPK_02`, …). *Alignment* ist die zeitliche Zuordnung der erkannten Wörter. *L1-Codierung* ist eine erste beschreibende Zuordnung von Inhalten (siehe Erweiterung unten).

## 1. Wofür eignet sich das Werkzeug?

Für Interviewvorbereitung, Oral History, Erschließung und anschließende qualitative Arbeit: Transkriptentwurf mit Zeitmarken, Trennung der Stimmen innerhalb einer Aufnahme, Hörstellen für die manuelle Prüfung, Stapelverarbeitung und eine Metadaten-Erweiterung (Entwurf, Vorschläge, Prüfliste). Ein maschineller Entwurf braucht menschliche Prüfung; er ist keine wissenschaftliche Interpretation und keine Feintranskription.

## 2. Wie weit ist die Version?

Version 0.3.2 (Oktober 2026). Echte lokale Transkription und Sprechertrennung wurden auf einem Mac-Entwicklungsrechner mit den festgelegten Modellrevisionen an einem selbst erzeugten 33-Sekunden-Testclip (zwei synthetische Stimmen) geprüft: 9 Segmente auf Deutsch, beide Stimmen korrekt getrennt. Es gibt 39 automatische Programmlogik-Prüfungen. **Nicht gemessen:** Windows-Installation, Erkennungsqualität an echten Interviews (Wort- und Sprecherfehlerrate), lange Aufnahmen, Offline-Lauf mit gesperrtem Netz, Sprachen außer Deutsch. Keine Angabe in diesem Dokument verspricht mehr.

## 3. Was brauche ich?

Einen Windows-11-Rechner (x64, CPU genügt), etwa 12 GB freien Speicher (einmalig ca. 3–4 GB für Laufzeit, Programmpakete, Decoder und Modelle) und einmalig Internet für die Einrichtung. Für die Sprechertrennung ist vorab eine kostenlose Freigabe auf der Modellseite nötig (Anleitung zeigt das Setup an); danach arbeitet alles offline. Keine Programmierkenntnisse, kein manuell gepflegtes Python, keine Admin-Rechte.

## 4. Wie beginne ich?

Das fertige Paket kommt vom Projektbetreuer (per Datei, z. B. USB-Stick); ein öffentlicher Download existiert noch nicht. Danach:

```powershell
# 1. Paket entpacken, z. B. nach C:\ohpipe-mini-windows
# 2. Einrichten (einmalig, lädt alles Notwendige mit Prüfung):
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Install.ps1
# 3. Neues PowerShell-Fenster öffnen, Selbsttest:
tests\smoke.cmd
# 4. Erste Aufnahme verarbeiten (genau ein Befehl):
oh-kette "C:\Users\Name\Downloads\Interview.mp4"
```

Die Einrichtung meldet Erfolg erst, wenn eine echte kurze Verarbeitung gelingt — nicht schon nach dem Entpacken. Details in [START-HIER.txt](START-HIER.txt) und [docs/HANDBUCH.md](docs/HANDBUCH.md).

## 5. Wie sieht ein Ergebnis aus?

Auszug aus dem geprüften Testclip (synthetische Stimmen, gekürzt):

```text
[00:00:00.0] SPK_02: Guten Tag und herzlich willkommen zu unserem Gespräch über das Leben auf dem Dorf.
[00:00:05.9] SPK_01: Guten Tag. Ich bin im Norden in einem kleinen Dorf aufgewachsen, mit einem Bauernhof nebenan.
[00:00:11.8] SPK_02: Wie war die Schule damals für Sie im Nachbarort? [SPK_01: Mhm.]
```

Eckige Klammern markieren kurze Einwürfe der anderen Stimme. Die Hörliste begründet jede Prüfstelle, z. B.:

```text
  1.    11.8 - 14.6  ( 2.8 s) Sprecherwechsel im Satz: ...
KONTROLLE   0.0 - 60.0 s: Zuordnung prüfen — SPK_02 spricht zuerst (Rollenvorschlag: fragend, unbestätigt).
```

Alle Beispiele in dieser Datei stammen aus dem Testclip und sind als solche gekennzeichnet.

## 6. Wie prüfe ich es?

Erste Minute anhören (Rollenkontrolle: Wer fragt, wer erzählt?), jede Hörstelle in der Aufnahme aufsuchen (`oh-hoer NAME 5` spielt ca. 15 Sekunden vor), Rollen mit `oh-rollen` bestätigen, Fehler im Transkript von Hand korrigieren. Die automatische Sprechertrennung erkennt Stimmen innerhalb einer Aufnahme; sie identifiziert keine reale Person. Korrigierte Dateien werden vor Neuberechnungen gesichert.

## 7. Welche Dateien bekomme ich?

Pro Aufnahme ein Ordner mit: `NAME.txt` (lesbar, mit Zeit und Sprecher), `NAME.srt` (Untertitel mit Zeitmarken), `NAME.json` (strukturiert: Segmente, Wörter mit Zeitquelle, Sprecher, Prüfhinweise, unbestätigte Rollen, technische Herkunft), `NAME.rttm` (Sprecherintervalle zum Austausch, z. B. für Auswertung), `NAME.hoerliste.txt` und `NAME.run.json` (Protokoll: Eingabe, Versionen, Parameter). Für menschliche Prüfung eignen sich TXT und Hörliste, für Untertitel SRT, für Weiterverarbeitung und Auswertung JSON und RTTM.

## 8. Was bleibt lokal?

Nach der Einrichtung soll die Verarbeitung ohne Internet funktionieren: Es wird nichts unbemerkt nachgeladen; fehlende Bestandteile brechen mit Einrichtungshinweis ab. Geprüft ist das bisher nur teilweise (echte Modellläufe liefen offline auf dem Entwicklungsrechner; ein Lauf mit vollständig gesperrtem Netz steht aus). Achtung: Wer seinen Ergebnisordner in OneDrive oder einen anderen synchronisierten Ordner legt, überträgt Dateien über dessen Dienst — dafür einen lokalen Ordner wählen (das Setup weist darauf hin).

## 9. Was sind die Grenzen?

Am Testclip (kleinstes Modell) traten z. B. auf: „Bauernhof nebenan“ → „Bauern hoffen nebenan“, „Nachbarort“ → „Barort“. Dialekt, Hintergrundgeräusche, Sprachwechsel, mehr als zwei Stimmen und Überlappung sind nicht an echten Aufnahmen geprüft; unsichere Stellen werden markiert, nicht verschwiegen. Maschinelle Trefferquoten sind keine wissenschaftliche Verlässlichkeit.

## 10. Welche Erweiterungen gibt es?

`oh-kette DATEI --voll` erstellt zusätzlich einen Metadatenentwurf, lokale Titel-/Zusammenfassungs-Vorschläge, eine Prüfung personenbezogener Hinweise und eine Prüfliste. Die Vorschläge entstehen derzeit durch festgelegte Regeln aus dem Transkript (kein Sprachmodell, keine Cloud). Einwilligung (`consent_status`) und Zugangsrechte (`accessRights`) setzt immer die zuständige Person von Hand — sie werden nie aus dem Gespräch erfunden. Die Übergabe an andere Systeme bleibt ein ausdrücklicher manueller Schritt.

## 11. Zitieren, Fragen, Mitwirken?

Zitierangaben stehen in [CITATION.cff](CITATION.cff). Fragen und Fehlerberichte bitte erst nach der Repositoryerstellung als Issue einreichen (Vorlagen liegen bei); nie Aufnahmen oder vollständige Transkripte hochladen. Vertiefung: [docs/METHODIK.md](docs/METHODIK.md) (Verfahren), [docs/DATENFORMATE.md](docs/DATENFORMATE.md) (Dateiformate), [docs/QUALITAET.md](docs/QUALITAET.md) (Tests und Grenzen), [docs/DATENSCHUTZ.md](docs/DATENSCHUTZ.md) (Daten und Netz), [docs/ENTWICKLUNG.md](docs/ENTWICKLUNG.md) (Technik), [docs/TESTBERICHT.md](docs/TESTBERICHT.md) (gemessener Stand).
