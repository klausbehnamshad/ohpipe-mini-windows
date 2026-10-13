"""Regression zu Pruefbericht 0.3.0: isolierter Start und Rollenkorrektur.

- Isolierter Start (`python -I`, wie Windows-Embed): Anwendungsmodule
  muessen ohne sys.path-Hilfe von aussen ladbar sein.
- `--setzt` parst ROLLE=SPK_xx-Paare und validiert sie (kein ungeparstes
  Speichern).
- `--tausch` tauscht Rollen, laesst stabile Sprecherkennungen (Segmente,
  Woerter, Turns, Exporte) unveraendert.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app" / "ohpipe.py"
sys.path.insert(0, str(ROOT / "app"))
import ohpipe  # noqa: E402
import ohext  # noqa: E402

NAME = "rollenprobe"


def _v2_fixture():
    """Vollstaendige Format-2-Daten: 2 Segmente, 6 Woerter, 1 Turn."""
    def w(i, text, s, e, sp, satz=0):
        return {"i": i, "text": text, "start": s, "end": e, "score": 0.9,
                "timed": True, "time_source": "faster-whisper",
                "speaker": sp, "speaker_raw": sp, "overlap": False,
                "overlap_speakers": [], "einwurf": False,
                "second_opinion": None, "sentence": satz}
    segments = [
        {"id": "seg0001", "start": 0.0, "end": 2.0, "text": "Wo sind Sie geboren?",
         "speaker": "SPK_01", "flags": []},
        {"id": "seg0002", "start": 2.5, "end": 5.0, "text": "Im Norden auf dem Dorf.",
         "speaker": "SPK_02", "flags": []},
    ]
    words = [w(0, "Wo", 0.0, 0.3, "SPK_01"), w(1, "sind", 0.3, 0.6, "SPK_01"),
             w(2, "Sie", 0.6, 0.9, "SPK_01"), w(3, "geboren?", 0.9, 1.4, "SPK_01"),
             w(4, "Im", 2.5, 2.8, "SPK_02", 1), w(5, "Norden", 2.8, 3.4, "SPK_02", 1),
             w(6, "auf", 3.4, 3.6, "SPK_02", 1), w(7, "dem", 3.6, 3.8, "SPK_02", 1),
             w(8, "Dorf.", 3.8, 4.4, "SPK_02", 1)]
    data = {"format": "ohpipe-mini-windows", "format_version": 2, "name": NAME,
            "language": "de", "roles": {}, "role_status": "unbestaetigt",
            "segments": segments, "words": words,
            "sentences": [
                {"i": 0, "start": 0.0, "end": 1.4, "speaker": "SPK_01",
                 "text": "Wo sind Sie geboren?", "sprecherwechsel_im_satz": False,
                 "kurzantwort": False},
                {"i": 1, "start": 2.5, "end": 4.4, "speaker": "SPK_02",
                 "text": "Im Norden auf dem Dorf.", "sprecherwechsel_im_satz": False,
                 "kurzantwort": False}],
            "turns": [{"speaker": "SPK_01", "start": 0.0, "end": 1.4,
                       "sentences": [0], "einwuerfe": []},
                      {"speaker": "SPK_02", "start": 2.5, "end": 4.4,
                       "sentences": [1], "einwuerfe": []}],
            "alignment": "faster-whisper", "tech": {}}
    odir = ohpipe.out_dir_for(NAME)
    odir.mkdir(parents=True, exist_ok=True)
    (odir / f"{NAME}.json").write_text(json.dumps(data, ensure_ascii=False),
                                       encoding="utf-8")
    # Bestehende Vollkette, damit die Veraltet-Markierung greift.
    ohext.meta_dir(NAME).mkdir(parents=True, exist_ok=True)
    for ext in (".txt", ".srt", ".rttm", ".hoerliste.txt"):
        (odir / f"{NAME}{ext}").write_text("ALT-" + ext, encoding="utf-8")
    return odir


@pytest.fixture()
def daten(tmp_path, monkeypatch):
    monkeypatch.setenv("OHPIPE_DATA", str(tmp_path / "daten"))
    return tmp_path


def _ns(d):
    return type("NS", (), d)()


def _laden():
    return json.loads((ohpipe.out_dir_for(NAME) / f"{NAME}.json").read_text("utf-8"))


def test_isolierter_start_laedt_erweiterung(daten, tmp_path):
    # Wie Windows-Embed (-I: kein Skriptordner, keine Umgebung im Pfad).
    r = subprocess.run([sys.executable, "-I", str(APP), "entwurf", "--help"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Warnung: Erweiterung nicht geladen" not in r.stderr


def test_isolierter_start_ohne_cwd_bezug(daten, tmp_path):
    r = subprocess.run([sys.executable, "-I", str(APP), "diagnose"],
                       capture_output=True, text=True, cwd=tmp_path,
                       env={"PATH": os.environ.get("PATH", ""),
                            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")})
    assert r.returncode in (0, 1), r.stderr
    assert "ModuleNotFoundError" not in r.stderr


def test_setzt_parst_und_validiert(daten):
    _v2_fixture()
    rc = ohext.cmd_rollen(_ns({"name": NAME, "tausch": False,
                               "setzt": ["fragend=SPK_01", "interviewt=SPK_02"]}))
    assert rc == 0
    data = _laden()
    assert data["roles"] == {"fragend": "SPK_01", "interviewt": "SPK_02"}
    assert data["role_status"] == "bestaetigt-hand"


def test_setzt_weist_unbekannte_rolle_zurueck(daten):
    _v2_fixture()
    rc = ohext.cmd_rollen(_ns({"name": NAME, "tausch": False,
                               "setzt": ["kamera=SPK_01"]}))
    assert rc == 2
    assert _laden()["roles"] == {}


def test_setzt_weist_doppelte_rolle_zurueck(daten):
    _v2_fixture()
    rc = ohext.cmd_rollen(_ns({"name": NAME, "tausch": False,
                               "setzt": ["fragend=SPK_01", "fragend=SPK_02"]}))
    assert rc == 2
    assert _laden()["roles"] == {}
    assert _laden()["role_status"] == "unbestaetigt"


def test_setzt_weist_doppelte_und_falsche_sprecher_zurueck(daten):
    _v2_fixture()
    assert ohext.cmd_rollen(_ns({"name": NAME, "tausch": False,
                                 "setzt": ["fragend=SPK_01", "interviewt=SPK_01"]})) == 2
    assert ohext.cmd_rollen(_ns({"name": NAME, "tausch": False,
                                 "setzt": ["fragend=SPK_09"]})) == 2
    assert ohext.cmd_rollen(_ns({"name": NAME, "tausch": False,
                                 "setzt": ["fragend"]})) == 2
    assert _laden()["roles"] == {}
    assert _laden()["role_status"] == "unbestaetigt"


def test_tausch_aendert_rollen_nicht_sprecher(daten):
    odir = _v2_fixture()
    vorher_txt = (odir / f"{NAME}.txt").read_text("utf-8")
    rc = ohext.cmd_rollen(_ns({"name": NAME, "tausch": True, "setzt": None}))
    assert rc == 0
    data = _laden()
    assert data["roles"] == {"fragend": "SPK_02", "interviewt": "SPK_01"}
    assert data["role_status"] == "bestaetigt-hand"
    # Stabile Kennungen: Segmente, Woerter, Turns und Exporte unveraendert.
    assert [s["speaker"] for s in data["segments"]] == ["SPK_01", "SPK_02"]
    assert {w["speaker"] for w in data["words"]} == {"SPK_01", "SPK_02"}
    assert [t["speaker"] for t in data["turns"]] == ["SPK_01", "SPK_02"]
    assert [s["speaker"] for s in data["sentences"]] == ["SPK_01", "SPK_02"]
    assert (odir / f"{NAME}.txt").read_text("utf-8") == vorher_txt
    assert (ohext.meta_dir(NAME) / "VERALTET.txt").is_file()
    assert (odir / f"{NAME}.json.bak").is_file()


def test_tausch_nur_bei_zwei_sprechern(daten):
    _v2_fixture()
    data = _laden()
    data["segments"].append({"id": "seg0003", "start": 6.0, "end": 7.0,
                             "text": "Moin.", "speaker": "SPK_03", "flags": []})
    (ohpipe.out_dir_for(NAME) / f"{NAME}.json").write_text(
        json.dumps(data), encoding="utf-8")
    assert ohext.cmd_rollen(_ns({"name": NAME, "tausch": True, "setzt": None})) == 2
