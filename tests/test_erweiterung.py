"""Erweiterungstests ohne Modelle/Netz: Entwurf, PII, L1, Rollen, Uebernahme (pytest)."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import tempfile
os.environ["OHPIPE_DATA"] = tempfile.mkdtemp(prefix="ohpipe-test-")

import ohpipe  # noqa: E402
import ohext  # noqa: E402

NAME = "erwprobe"


def seg(i, start, end, text, speaker):
    return {"id": f"seg{i:04d}", "start": start, "end": end, "text": text,
            "speaker": speaker, "flags": [], "lang": "de"}


@pytest.fixture()
def transkript():
    segs = [
        seg(1, 0.0, 4.0, "Guten Tag Frau Berger, erzaehlen Sie von Ihrer Kindheit im Dorf?", "SPK_01"),
        seg(2, 4.0, 9.0, "Ich bin in einem kleinen Dorf im Norden aufgewachsen mit Bauernhof.", "SPK_02"),
        seg(3, 9.0, 9.6, "Mhm.", "SPK_01"),
        seg(4, 9.6, 15.0, "Meine Eltern arbeiteten frueh bis spaet auf den Feldern damals.", "SPK_02"),
        seg(5, 15.0, 19.0, "Wie war die Schule im Nachbarort damals fuer Sie?", "SPK_01"),
        seg(6, 19.0, 26.0, "Die Schule war streng, der Lehrer Herr Meyer verteilte Strafarbeiten.", "SPK_02"),
        seg(7, 26.0, 31.0, "Schreiben Sie mir an maria.berger@example.org oder rufen Sie 01234 567890 an.", "SPK_02"),
        seg(8, 31.0, 36.0, "Wir wohnten in der Bergstrasse 12, das Haus steht heute noch.", "SPK_02"),
        seg(9, 36.0, 40.0, "Was haben Sie nach der Schule gemacht?", "SPK_01"),
        seg(10, 40.0, 47.0, "Ich lernte Schneiderin und arbeitete in der Fabrik am Stadtrand.", "SPK_02"),
        seg(11, 47.0, 47.4, "Ja.", "SPK_01"),
        seg(12, 47.4, 53.0, " spaeter zog ich in die Stadt und gruendete eine Familie dort.", "SPK_02"),
    ]
    odir = ohpipe.out_dir_for(NAME)
    odir.mkdir(parents=True, exist_ok=True)
    (odir / f"{NAME}.json").write_text(json.dumps(
        {"format": "ohpipe-mini-windows", "format_version": 1, "name": NAME,
         "language": "de", "roles": {}, "role_status": "unbestaetigt",
         "segments": segs, "tech": {}}, ensure_ascii=False), encoding="utf-8")
    return segs


def test_entwurf_rechte_bleiben_leer(transkript):
    record, prov, _ = ohext.build_draft(NAME)
    assert record["consent_status"] == "" and record["accessRights"] == ""
    assert record["language"] == "deu"
    assert record["title"].startswith("TODO")
    assert prov["imm_core"] == "1.1.0"


def test_vorschlaege_form(transkript):
    v = ohext.build_vorschlaege(NAME)
    assert len(v["titel_optionen"]) == 3
    assert 6 <= len(v["schlagwoerter"]) <= 10
    assert v["segmentnamen"]
    assert "Personennamen" in v["hinweis"]


def test_pii_findet_email_anrede_telefon(transkript):
    hits = ohext.pii_check(NAME)
    arten = {h["art"] for h in hits}
    assert {"e-mail", "anrede-name", "telefon"} <= arten


def test_l1_kurz_und_verankert(transkript):
    res = ohext.build_l1(NAME)
    codes = {c["segment"]: c for c in res["rohcodes"]}
    assert codes["seg0003"]["code"] == "KURZ" and codes["seg0011"]["code"] == "KURZ"
    assert res["statistik"]["anteil_verankert"] >= 0.9
    assert len(res["kategorien"]) <= 15
    assert res["codebuch_format"] == "ohpipe.l1.codebook.v1"


def test_l1_nur_fragen(transkript):
    res = ohext.build_l1(NAME, nur_fragen=True)
    assert len(res["fragenleitfaden"]) >= 3
    assert res["rollen_status"] == "unbestaetigt"


def test_voll_uebernehmen_rollen_kette(transkript):
    assert ohext.voll_chain(NAME) == 0
    mdir = ohext.meta_dir(NAME)
    for ext in (".imm.draft.json", ".imm.provenance.json", ".entwurf.json",
                ".pii.json", ".pruefliste.txt"):
        assert (mdir / f"{NAME}{ext}").is_file(), ext
    ns = {"name": NAME, "felder": ["titel", "keywords"], "titel_nr": 2}
    assert ohext.cmd_uebernehmen(_ns(ns)) == 0
    draft = json.loads((mdir / f"{NAME}.imm.draft.json").read_text("utf-8"))
    assert not draft["title"].startswith("TODO")
    assert (mdir / f"{NAME}.imm.draft.bak.json").is_file()
    assert ohext.cmd_rollen(_ns({"name": NAME, "tausch": True, "setzt": None})) == 0
    data = json.loads((ohpipe.out_dir_for(NAME) / f"{NAME}.json").read_text("utf-8"))
    assert data["role_status"] == "bestaetigt-hand"
    assert (mdir / "VERALTET.txt").is_file()
    assert ohext.cmd_l1(_ns({"name": NAME, "codebuch": None,
                             "nur_fragen": False, "neu": False})) == 0
    assert (mdir / f"{NAME}.l1.entwurf.json").is_file()
    assert (mdir / f"{NAME}.codebuch.vorschlag.toml").is_file()


def _ns(d):
    return type("NS", (), d)()
