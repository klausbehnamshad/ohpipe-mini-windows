"""Gemeinsame Merge-Regression (modellunabhaengig) und Adaptertests.

Identische Wortdaten + Sprecherintervalle muessen nachvollziehbar dieselben
Entscheidungen liefern — unabhaengig von ASR- und Diarisierungsmodell.
Faelle: Einwurf vs. Antwort nach Frage, Wechsel im Satz, Ueberlappung,
fehlende Wortzeiten, mehr als zwei Stimmen. Kein Beweis identischer
Erkennungsqualitaet auf Mac und Windows.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import diar2_merge as m  # noqa: E402
import diar_adapter as adapter  # noqa: E402


def seq(text, start, step=0.3, gap=0.05):
    out, t = [], start
    for tok in text.split():
        out.append((tok, round(t, 3), round(t + step, 3)))
        t += step + gap
    return out


def words_data(wortliste, lang="de"):
    return {"alignment": "faster-whisper", "model": "tiny", "language": lang,
            "segments": [{"start": 0.0, "end": 99.0, "text": "",
                          "words": [{"word": t, "start": s, "end": e,
                                     "score": 0.9, "time_source": "faster-whisper"}
                                    for t, s, e in wortliste]}]}


def run_merge(wortliste, turns, tmp_path, name="fall"):
    wd = words_data(wortliste)
    (tmp_path / "w.json").write_text(
        __import__("json").dumps(wd), encoding="utf-8")
    rttm = tmp_path / "p.rttm"
    rttm.write_text("".join(
        f"SPEAKER {name} 1 {a:.3f} {b - a:.3f} <NA> <NA> {sp} <NA> <NA>\n"
        for a, b, sp in turns), encoding="utf-8")
    return m.run(tmp_path / "w.json", rttm, tmp_path / "out", None, "-")


def test_einwurf_bleibt_einwurf(tmp_path):
    # „Mhm“ waehrend der andere spricht: Einwurf, kein eigener Turn.
    w = (seq("Ich bin damals aufs Feld gegangen", 0.0)
         + [("Mhm.", 1.0, 1.4)]
         + seq("und habe dort gearbeitet", 2.0))
    turns = [(0.0, 4.0, "SPK_02"), (0.9, 1.5, "SPK_01")]
    res = run_merge(w, turns, tmp_path)
    einwuerfe = [e for t in res["turns"] for e in t["einwuerfe"]]
    assert any("Mhm" in e["text"] for e in einwuerfe)
    # Kein eigener SPK_01-Turn nur fuer den Einwurf.
    assert not [t for t in res["turns"]
                if t["speaker"] == "SPK_01" and not t["einwuerfe"]
                and len(t["sentences"]) == 1]


def test_ja_nach_frage_ist_antwort(tmp_path):
    w = seq("Wo sind Sie geboren?", 0.0) + seq("Ja.", 2.0)
    turns = [(0.0, 1.5, "SPK_01"), (1.9, 2.6, "SPK_02")]
    res = run_merge(w, turns, tmp_path)
    antworten = [s for s in res["sentences"] if s["kurzantwort"]]
    assert len(antworten) == 1
    assert "Ja" in antworten[0]["text"]
    assert not any(wd.get("einwurf") for wd in res["words"]
                   if wd["sentence"] == antworten[0]["i"])


def test_wechsel_im_satz_wird_geteilt_und_gelistet(tmp_path):
    a = seq("und dann sind wir nach Berlin gezogen", 0.0)
    b = seq("wann war das ungefähr genau?", a[-1][2] + 0.1)
    w = a + b
    turns = [(0.0, a[-1][2] + 0.05, "SPK_01"), (a[-1][2] + 0.05, 9.0, "SPK_02")]
    res = run_merge(w, turns, tmp_path)
    assert any(s["sprecherwechsel_im_satz"] for s in res["sentences"])
    assert any(it["art"] == "Sprecherwechsel im Satz" for it in res["hoerliste"])


def test_fehlende_wortzeiten_werden_geschaetzt_und_markiert(tmp_path):
    segmente = [{"id": "seg0001", "start": 0.0, "end": 4.0,
                 "text": "Guten Tag wie geht es", "speaker": None, "flags": []}]
    wd = adapter.build_words_data(segmente, "de", "tiny")
    assert wd["alignment"] == "segment-fallback"
    assert "alignment_hinweis" in wd
    quellen = {w["time_source"] for s in wd["segments"] for w in s["words"]}
    assert quellen == {"geschaetzt-segment"}
    # Zeiten liegen innerhalb der Segmentspranne, nie davor/dahinter.
    for s in wd["segments"]:
        for w in s["words"]:
            assert 0.0 <= w["start"] <= w["end"] <= 4.0


def test_drei_sprecher_ohne_zweipersonenrollen(tmp_path):
    w = seq("Hallo zusammen.", 0.0) + seq("Guten Tag.", 2.0) + seq("Moin.", 4.0)
    turns = [(0.0, 1.0, "SPK_01"), (2.0, 3.0, "SPK_02"), (4.0, 5.0, "SPK_03")]
    res = run_merge(w, turns, tmp_path)
    labels = {t["speaker"] for t in res["turns"]}
    assert labels == {"SPK_01", "SPK_02", "SPK_03"}
    vorschlag = adapter.rollenvorschlag(res)
    assert vorschlag["status"] == "unbestaetigt-vorschlag"
    assert "oh-rollen" in vorschlag["hinweis"]


def test_rttm_export_entspricht_geglaetteten_intervallen(tmp_path):
    w = (seq("Ich bin damals aufs Feld gegangen", 0.0)
         + seq("Das war eine schwere Zeit.", 5.0))
    turns = [(0.0, 3.0, "SPK_02"), (5.0, 7.5, "SPK_01")]
    res = run_merge(w, turns, tmp_path)
    # Adapterableitung gegen Modul-Referenz (gerenderter RTTM-Text exakt).
    import io
    words = m.load_words({"alignment": "faster-whisper",
                          "segments": [{"start": 0.0, "end": 99.0, "text": "",
                                        "words": [{"word": t, "start": s, "end": e}
                                                  for t, s, e in w]}]})
    segs = [m.Seg(a, b, sp) for a, b, sp in turns]
    m.assign_raw(words, segs)
    sents = m.smooth(m.split_sentences(words))
    turns_m = m.build_turns(sents)
    ref_pfad, neu_pfad = tmp_path / "ref.rttm", tmp_path / "neu.rttm"
    m.write_rttm(ref_pfad, m.smoothed_segments(turns_m, sents), recording_id="x")
    m.write_rttm(neu_pfad, [m.Seg(a, b, sp)
                            for a, b, sp in adapter.smoothed_rttm_entries(res)],
                 recording_id="x")
    assert neu_pfad.read_text() == ref_pfad.read_text()
    assert len(adapter.smoothed_rttm_entries(res)) > 0


def test_v1_segmente_ohne_woerter_laufen_mit_fallback(tmp_path):
    # Migrationsfall: Format-1-Ergebnis (Segmente ohne Woerter) bleibt lesbar.
    segmente = [{"id": "seg0001", "start": 0.5, "end": 3.2, "text": "Guten Tag.",
                 "speaker": "SPK_01", "flags": []}]
    wd = adapter.build_words_data(segmente, "de", "base")
    assert wd["alignment"] == "segment-fallback"
    res = adapter.run_merge(wd, [(0.0, 4.0, "SPK_01")], "mig", tmp_path, {})
    assert res["sentences"] and res["sentences"][0]["speaker"] == "SPK_01"
