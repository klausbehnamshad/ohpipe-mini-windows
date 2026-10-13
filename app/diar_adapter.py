#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter von Windows-Modellresultaten auf diar2_merge (Wortebene).

faster-whisper liefert echte Wortzeiten (time_source „faster-whisper“),
pyannote-3.1 die Sprecherintervalle. diar2_merge vergibt Sprecher pro Wort,
glaettet, erkennt Einwuerfe und liefert die Pruefstellen mit Grund.
Fehlende Wortzeiten werden ausdruecklich als Schaetzung gekennzeichnet
(time_source „geschaetzt-segment“, alignment „segment-fallback“); sie
erscheinen nie als gemessene Wortzeiten.
"""
from __future__ import annotations

import json
from pathlib import Path

import diar2_merge as merge

ALIGNMENT = "faster-whisper"
FALLBACK_ALIGNMENT = "segment-fallback"


def build_words_data(segments: list[dict], lang: str, asr_model: str) -> dict:
    """ASR-Segmente (mit Woertern, soweit vorhanden) -> diar2-Wort-JSON."""
    out_segs = []
    fallback = False
    for s in segments:
        worte = []
        woerter = s.get("words") or []
        timed = [w for w in woerter
                 if w.get("start") is not None and w.get("end") is not None]
        if timed:
            for w in woerter:
                text = (w.get("word") if w.get("word") is not None
                        else w.get("text", "")).strip()
                if not text:
                    continue
                if w.get("start") is not None and w.get("end") is not None:
                    worte.append({"word": text, "start": float(w["start"]),
                                  "end": float(w["end"]),
                                  "score": w.get("score", w.get("probability")),
                                  "time_source": "faster-whisper"})
                else:
                    worte.append({"word": text, "start": None, "end": None,
                                  "score": w.get("score", w.get("probability"))})
        else:
            # Rueckfall: Woerter gleichmaessig ueber die Segmentspranne legen,
            # als Schaetzung kennzeichnen (keine gemessenen Zeiten).
            fallback = True
            tokens = (s.get("text") or "").split()
            span = max(float(s["end"]) - float(s["start"]), 0.01)
            step = span / max(len(tokens), 1)
            for k, tok in enumerate(tokens):
                worte.append({"word": tok,
                              "start": round(float(s["start"]) + k * step, 3),
                              "end": round(float(s["start"]) + (k + 1) * step, 3),
                              "score": None, "time_source": "geschaetzt-segment"})
        out_segs.append({"start": float(s["start"]), "end": float(s["end"]),
                         "text": s.get("text", ""), "words": worte})
    data = {"alignment": FALLBACK_ALIGNMENT if fallback else ALIGNMENT,
            "model": asr_model, "language": lang, "segments": out_segs}
    if fallback:
        data["alignment_hinweis"] = (
            "Keine ASR-Wortzeiten verfuegbar; Woerter wurden proportional auf die "
            "Segmentspanne gelegt (time_source geschaetzt-segment). "
            "Sprecherzuordnung dadurch groeber — Pruefhinweise beachten.")
    return data


def build_rttm_segs(turns: list[tuple]) -> list:
    """Diar-Turns (start, ende, label) -> sortierte merge.Seg-Liste."""
    segs = [merge.Seg(float(a), float(b), str(sp)) for a, b, sp in turns
            if float(b) > float(a)]
    segs.sort(key=lambda s: (s.start, s.end))
    return segs


def run_merge(words_data: dict, turns: list[tuple], name: str,
              workdir: Path, meta: dict) -> dict:
    """Schreibt Eingaben in workdir, laesst diar2_merge laufen, gibt result."""
    workdir.mkdir(parents=True, exist_ok=True)
    wpfad = workdir / "merge-woerter.json"
    rpfad = workdir / "merge-primaer.rttm"
    wpfad.write_text(json.dumps(words_data, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    merge.write_rttm(rpfad, build_rttm_segs(turns), recording_id=name)
    # Kein unkontrollierter Code-Download: Modul liegt in app/ bei.
    # Keine Zweitmeinung (nur ein Diarisierungsmodell): second=None.
    return merge.run(wpfad, rpfad, workdir / "merge", None, "-", meta)


def sentences_to_segments(result: dict) -> list[dict]:
    """Merge-Saetze -> Windows-Segmente (mit Pruefhinweisen aus der Logik)."""
    segs = []
    for s in result.get("sentences", []):
        flags = []
        if s.get("sprecherwechsel_im_satz"):
            flags.append("pruefen:sprecherwechsel-im-satz")
        if s.get("kurzantwort"):
            flags.append("hinweis:kurzantwort-nach-frage")
        woerter = [w for w in result.get("words", []) if w.get("sentence") == s["i"]]
        if any(w.get("overlap") for w in woerter):
            flags.append("heuristik:ueberlappung-oder-unsicher")
        if all(w.get("einwurf") for w in woerter):
            flags.append("heuristik:einwurf")
        elif len((s.get("text") or "").split()) < 4:
            flags.append("heuristik:kurz-einwurf")
        if s["end"] - s["start"] < 1.0 and not s.get("kurzantwort"):
            flags.append("heuristik:sehr-kurzer-turn-pruefen")
        segs.append({"id": f"seg{s['i'] + 1:04d}", "start": s["start"],
                     "end": s["end"], "text": s["text"],
                     "speaker": s["speaker"], "flags": sorted(set(flags))})
    return segs


def review_to_hoerliste(result: dict, erste_stimme: str | None) -> str:
    """Merge-Pruefstellen (mit Grund) -> Windows-Hoerliste inkl. Rollenkontrolle."""
    items = result.get("hoerliste", [])
    hidden = result.get("hoerliste_ausgeblendet", [])
    lines = ["Pruefstellen (mit Grund) — erste Minute zur Rollenkontrolle pruefen:",
             ""]
    if erste_stimme:
        lines.append(f"KONTROLLE   0.0 - 60.0 s: Zuordnung pruefen — {erste_stimme} "
                     f"spricht zuerst (Rollenvorschlag: fragend, unbestaetigt).")
        lines.append("")
    for n, it in enumerate(items, 1):
        lines.append(f'{n:3d}. {it["start"]:07.1f} - {it["end"]:07.1f} '
                     f'({it["end"] - it["start"]:4.1f} s) {it["art"]}: '
                     f'{it.get("text", "")[:120]}')
    if not items:
        lines.append("Keine unsicheren Stellen markiert.")
    if hidden:
        gr = {}
        for h in hidden:
            gr[h.get("grund", "?")] = gr.get(h.get("grund", "?"), 0) + 1
        lines.append("")
        lines.append("Ausgeblendete Überlappungen: "
                     + ", ".join(f"{k} ({v})" for k, v in sorted(gr.items()))
                     + " — Details in NAME.json.")
    return "\n".join(lines) + "\n"


def smoothed_rttm_entries(result: dict) -> list:
    """Geglaettete Sprecherintervalle (start, ende, speaker) aus dem Ergebnis.

    Entspricht merge.smoothed_segments(turns, sentences) auf Dikten:
    Hauptspanne je Satz plus Einwuerfe aus den Turns.
    """
    eintraege = []
    woerter = result.get("words", [])
    for s in result.get("sentences", []):
        main = [w for w in woerter
                if w.get("sentence") == s["i"] and w.get("speaker") == s.get("speaker")]
        if main:
            eintraege.append((main[0]["start"], main[-1]["end"], s.get("speaker")))
    for t in result.get("turns", []):
        for e in t.get("einwuerfe", []):
            eintraege.append((e["start"], e["end"], e.get("speaker")))
    eintraege = [(a, b, sp) for a, b, sp in eintraege if sp and b > a]
    eintraege.sort(key=lambda e: (e[0], e[1]))
    return eintraege


def rollenvorschlag(result: dict) -> dict:
    """Hoechstens ein deutlich markierter Vorschlag fuer die erste Stimme."""
    turns = result.get("turns", [])
    if not turns:
        return {"status": "kein-vorschlag"}
    erste = turns[0].get("speaker")
    return {"erste_stimme": erste, "vorschlag": "fragend",
            "status": "unbestaetigt-vorschlag",
            "hinweis": ("Automatische Kennungen bezeichnen nur Stimmen innerhalb dieser "
                        "Aufnahme. Rollen bitte mit oh-rollen bestaetigen.")}
