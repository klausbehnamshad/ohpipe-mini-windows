"""Kern-Tests ohne Modelle: Export, Namen, Wiederaufnahme-Marker (pytest)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import ohpipe


def segs():
    return [
        {"id": "seg0001", "start": 0.5, "end": 3.2, "text": "Guten Tag.", "speaker": "SPK_01",
         "flags": []},
        {"id": "seg0002", "start": 3.2, "end": 7.9, "text": "Ich erzaehle gern.", "speaker": "SPK_02",
         "flags": ["heuristik:kurz-einwurf"]},
    ]


def test_txt_enthaelt_zeit_und_sprecher():
    t = ohpipe.write_txt(segs())
    assert "[00:00:00.5] SPK_01: Guten Tag." in t
    assert "Hinweis" in t


def test_srt_gueltig_und_geordnet():
    s = ohpipe.write_srt(segs())
    assert "1\n00:00:00,500 --> 00:00:03,200\nSPK_01: Guten Tag." in s
    assert s.index("00:00:00,500") < s.index("00:00:03,200")


def test_json_versioniert_und_innerhalb_dauer():
    j = ohpipe.write_json("probe", segs(), {"duration": 60.0, "tech": {}})
    assert j["format_version"] == ohpipe.JSON_FORMAT
    assert all(x["end"] <= 61.0 for x in j["segments"])
    assert j["role_status"] == "unbestaetigt"


def test_reservierte_namen_werden_entschärft():
    assert ohpipe.safe_name("con") != "con"
    assert ohpipe.safe_name(" Interview: Test? ") not in ("", "con")


def test_nur_transkript_kennzeichnet_sprecher_offen():
    s = segs()
    for x in s:
        x["speaker"] = "SPK_??"
    j = ohpipe.write_json("probe", s, {"duration": 60.0, "tech": {}})
    assert all(x["speaker"] == "SPK_??" for x in j["segments"])
