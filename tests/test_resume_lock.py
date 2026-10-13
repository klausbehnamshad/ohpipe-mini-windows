"""Regression: Wiederaufnahme, Fehlerstatus, Lock, Interview-ID, ASR-Cache.

Echte Inferenz wird durch gezaehlte Fakes ersetzt; geprueft wird die
Steuerlogik: Unveraenderte Zweitlaeufe (Kern, nur-Transkript, Vollkette)
starten keine Inferenz neu, Sprecherfehler geben Exitcode 4 und werden
gezielt wiederholt, fremde Locks bleiben erhalten.
"""
import json
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import ohpipe  # noqa: E402


def _wav(path: Path, secs: float = 1.0, ton: int = 440) -> Path:
    import math
    import struct
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(16000 * secs)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * ton * i / 16000)))
            for i in range(n)))
    return path


def _ns(datei, **kw):
    d = {"datei": str(datei), "sprache": "de", "sprecher": None, "spur": None,
         "profil": "standard", "nur_transkript": False, "voll": False,
         "neu": False, "mock_transkript": None}
    d.update(kw)
    return type("NS", (), d)()


def _fake_engine(monkeypatch, zaehler, diar_ok=True, mit_modell=True):
    import os
    if mit_modell:
        # Eingerichtete (nicht leere) Diarisierungsablage vortaeuschen.
        mdir = Path(os.environ["OHPIPE_DATA"]) / "modelle" / "diar"
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / "test-modell.bin").write_bytes(b"fake")

    def fake_transcribe(wav, lang, model):
        zaehler["asr"] += 1
        return [
            {"id": "seg0001", "start": 0.0, "end": 0.5,
             "text": "Guten Tag.", "speaker": None, "flags": []},
            {"id": "seg0002", "start": 0.5, "end": 0.9,
             "text": "Mhm.", "speaker": None, "flags": []},
        ]

    def fake_diarize_turns(wav, n_speakers, diar_dir):
        zaehler["diar"] += 1
        if not diar_ok:
            raise RuntimeError("Test-Diarfehler")
        # Zwei Turns passend zu fake_transcribe (0.0-0.5, 0.5-0.9).
        return [(0.0, 0.5, "SPK_01"), (0.5, 0.9, "SPK_02")]

    monkeypatch.setattr(ohpipe, "transcribe", fake_transcribe)
    monkeypatch.setattr(ohpipe, "diarize_turns", fake_diarize_turns)


def _name_dir(tmp):
    name = ohpipe.interview_id(
        Path("x.wav"), {"sha256": "0" * 64, "bytes": 1, "mtime": 1.0})
    assert "--" in name
    return name


def test_zweitlauf_startet_keine_inferenz(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Interview.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    assert ohpipe.cmd_kette(_ns(src)) == 0
    assert (zaehler["asr"], zaehler["diar"]) == (1, 1)
    assert ohpipe.cmd_kette(_ns(src)) == 0
    assert (zaehler["asr"], zaehler["diar"]) == (1, 1), \
        "unveraenderter Zweitlauf darf keine Inferenz neu starten"
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    run = json.loads((ohpipe.out_dir_for(name) / f"{name}.run.json").read_text("utf-8"))
    assert run["status"] == "fertig"
    assert run["schritte"] == {"asr": "skip", "diar": "skip"}


def test_nur_transkript_zweitlauf_startet_keine_inferenz(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Kurz.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    assert ohpipe.cmd_kette(_ns(src, nur_transkript=True)) == 0
    assert zaehler["asr"] == 1 and zaehler["diar"] == 0
    assert ohpipe.cmd_kette(_ns(src, nur_transkript=True)) == 0
    assert zaehler["asr"] == 1, "reine Transkription muss wiederaufnehmbar sein"
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    run = json.loads((ohpipe.out_dir_for(name) / f"{name}.run.json").read_text("utf-8"))
    assert run["status"] == "teilweise (nur-transkript)"


def test_nur_transkript_upgrade_nutzt_transkript_ohne_neue_asr(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Upgrade.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    assert ohpipe.cmd_kette(_ns(src, nur_transkript=True)) == 0
    assert ohpipe.cmd_kette(_ns(src)) == 0
    assert zaehler["asr"] == 1 and zaehler["diar"] == 1
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    run = json.loads((ohpipe.out_dir_for(name) / f"{name}.run.json").read_text("utf-8"))
    assert run["status"] == "fertig"
    assert run["schritte"]["asr"] in ("datei", "cache")


def test_diarfehler_exit4_transkript_bleibt_retry_nur_diar(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Fehler.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler, diar_ok=False)
    rc = ohpipe.cmd_kette(_ns(src))
    assert rc == 4
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    odir = ohpipe.out_dir_for(name)
    assert (odir / f"{name}.txt").is_file(), "Transkript muss erhalten bleiben"
    run = json.loads((odir / f"{name}.run.json").read_text("utf-8"))
    assert run["status"] == "teilweise (diarisierung-fehlgeschlagen)"
    _fake_engine(monkeypatch, zaehler, diar_ok=True)
    assert ohpipe.cmd_kette(_ns(src)) == 0
    assert zaehler["asr"] == 1, "Wiederholung darf ASR nicht neu starten"
    assert zaehler["diar"] == 2
    run = json.loads((odir / f"{name}.run.json").read_text("utf-8"))
    assert run["status"] == "fertig"


def test_voll_zweitlauf_ohne_inferenz(tmp_path, monkeypatch):
    import ohext
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Voll.wav")
    zaehler = {"asr": 0, "diar": 0, "voll": 0}
    _fake_engine(monkeypatch, zaehler)
    orig_voll = ohext.voll_chain

    def fake_voll(name):
        zaehler["voll"] += 1
        return orig_voll(name)

    monkeypatch.setattr(ohext, "voll_chain", fake_voll)
    assert ohpipe.cmd_kette(_ns(src, voll=True)) == 0
    assert (zaehler["asr"], zaehler["diar"], zaehler["voll"]) == (1, 1, 1)
    assert ohpipe.cmd_kette(_ns(src, voll=True)) == 0
    assert (zaehler["asr"], zaehler["diar"], zaehler["voll"]) == (1, 1, 1), \
        "unveraenderter --voll-Zweitlauf darf nichts neu starten"


def test_fremder_lock_bleibt_erhalten(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Gesperrt.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    odir = ohpipe.out_dir_for(name)
    odir.mkdir(parents=True, exist_ok=True)
    (odir / ".lock").write_text("12345", encoding="utf-8")
    assert ohpipe.cmd_kette(_ns(src)) == 3
    assert (odir / ".lock").is_file(), "fremder Lock darf nicht entfernt werden"
    assert zaehler == {"asr": 0, "diar": 0}


def test_gleicher_dateiname_verschiedener_inhalt(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    a = _wav(tmp_path / "a" / "Gleich.wav", ton=440)
    b = _wav(tmp_path / "b" / "Gleich.wav", ton=880)
    assert ohpipe.cmd_kette(_ns(a)) == 0
    assert ohpipe.cmd_kette(_ns(b)) == 0
    na = ohpipe.interview_id(a, ohpipe.file_identity(a))
    nb = ohpipe.interview_id(b, ohpipe.file_identity(b))
    assert na != nb, "verschiedene Inhalte brauchen verschiedene Ordner"
    assert (ohpipe.out_dir_for(na) / f"{na}.txt").is_file()
    assert (ohpipe.out_dir_for(nb) / f"{nb}.txt").is_file()


def test_manuelle_aenderung_wird_vor_neuberechnung_gesichert(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Handarbeit.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    assert ohpipe.cmd_kette(_ns(src)) == 0
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    jpath = ohpipe.out_dir_for(name) / f"{name}.json"
    data = json.loads(jpath.read_text("utf-8"))
    data["segments"][0]["text"] = "HANDKORREKTUR"
    jpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert ohpipe.cmd_kette(_ns(src, sprecher=2)) == 0
    bak = ohpipe.out_dir_for(name) / f"{name}.json.bak"
    assert bak.is_file()
    assert "HANDKORREKTUR" in bak.read_text("utf-8")


def test_leere_modellablage_zaehlt_nicht_als_eingerichtet(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "OhneModell.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler, mit_modell=False)
    assert ohpipe.cmd_kette(_ns(src)) == 4
    assert zaehler["diar"] == 0, "ohne Modell darf keine Diarisierung starten"
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    run = json.loads((ohpipe.out_dir_for(name) / f"{name}.run.json").read_text("utf-8"))
    assert run["status"] == "teilweise (diarisierung-fehlgeschlagen)"


def test_modellwechsel_startet_inferenz_neu(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Revision.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler)
    assert ohpipe.cmd_kette(_ns(src)) == 0
    assert zaehler["asr"] == 1
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    run_path = ohpipe.out_dir_for(name) / f"{name}.run.json"
    # Echte Modellrevision in der Konfiguration aendern (nicht die Aufzeichnung).
    import copy
    echte_cfg = ohpipe.models_config()

    def geaenderte_cfg():
        c = copy.deepcopy(echte_cfg)
        c["asr"]["modelle"]["base"]["revision"] = "1" * 40
        return c

    monkeypatch.setattr(ohpipe, "models_config", geaenderte_cfg)
    assert ohpipe.cmd_kette(_ns(src)) == 0
    assert zaehler["asr"] == 2, "geaenderte Modellrevision muss neu berechnen"
    assert (ohpipe.out_dir_for(name) / f"{name}.json.bak").is_file()


def test_zwei_konkurrierende_laeufe(tmp_path, monkeypatch):
    import threading
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Rennen.wav")
    zaehler = {"asr": 0, "diar": 0}
    freigabe = threading.Event()

    def langsam_transcribe(wav, lang, model):
        zaehler["asr"] += 1
        assert freigabe.wait(timeout=30), "Freigabe kam nicht"
        return [{"id": "seg0001", "start": 0.0, "end": 0.5, "text": "Hallo.",
                 "speaker": None, "flags": []}]

    def turns(wav, n_speakers, diar_dir):
        zaehler["diar"] += 1
        return [(0.0, 0.5, "SPK_01")]

    import os
    mdir = Path(os.environ["OHPIPE_DATA"]) / "modelle" / "diar"
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "test-modell.bin").write_bytes(b"fake")
    monkeypatch.setattr(ohpipe, "transcribe", langsam_transcribe)
    monkeypatch.setattr(ohpipe, "diarize_turns", turns)
    ergebnis = {}

    def erster():
        ergebnis["rc1"] = ohpipe.cmd_kette(_ns(src))

    t = threading.Thread(target=erster)
    t.start()
    import time
    time.sleep(2.0)  # erster Lauf haelt den Lock (wartet in transcribe)
    ergebnis["rc2"] = ohpipe.cmd_kette(_ns(src))
    freigabe.set()
    t.join(timeout=60)
    assert ergebnis["rc2"] == 3, "zweiter Lauf muss belegt melden"
    assert ergebnis["rc1"] == 0
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    assert not (ohpipe.out_dir_for(name) / ".lock").is_file(), \
        "eigener Lock muss nach Abschluss weg sein"


def test_asr_cache_enthaelt_revision_und_wird_genutzt(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    src = _wav(tmp_path / "Cache.wav")
    zaehler = {"asr": 0, "diar": 0}
    _fake_engine(monkeypatch, zaehler, diar_ok=False)
    assert ohpipe.cmd_kette(_ns(src)) == 4
    name = ohpipe.interview_id(src, ohpipe.file_identity(src))
    workdir = ohpipe.out_dir_for(name).parent.parent / ".work" / name
    cache = json.loads((workdir / "asr-cache.json").read_text("utf-8"))
    assert len(cache["segments"]) == 2
    assert cache["asr"]["modell"] == "base"
