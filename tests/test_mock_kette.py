"""Entwicklungstest mit vorgegebenem Transkript (Mock, pytest).

Prueft Dateiablauf, Export und Wiederaufnahme OHNE Modelle. Darf nie als
Nachweis echter Transkription oder Sprechertrennung gelten — dafuer gibt es
tests/selbsttest_echt.py mit dem mitgelieferten Sprachclip.
"""
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app" / "ohpipe.py"
sys.path.insert(0, str(ROOT / "app"))
import ohpipe  # noqa: E402


def make_wav(path: Path, secs: float = 2.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * secs))


def test_mock_kette_export_und_wiederaufnahme(tmp_path):
    tmp = tmp_path / "mock"
    daten = tmp / "daten"
    os.environ["OHPIPE_DATA"] = str(daten)
    try:
        src = tmp / "Test Aufnahme (Umlaute äöü & 'Klammern').wav"
        make_wav(src)
        mock = tmp / "mock.json"
        mock.write_text(json.dumps([
            {"id": "seg0001", "start": 0.2, "end": 1.0, "text": "Guten Tag.",
             "speaker": "SPK_01", "flags": []},
            {"id": "seg0002", "start": 1.0, "end": 1.9, "text": "Mhm.",
             "speaker": "SPK_02", "flags": ["heuristik:kurz-einwurf"]},
        ]), encoding="utf-8")
        r1 = subprocess.run([sys.executable, str(APP), "kette", str(src),
                             "--mock-transkript", str(mock), "--nur-transkript"],
                            capture_output=True, text=True)
        assert r1.returncode == 0, r1.stderr
        name = ohpipe.interview_id(src, ohpipe.file_identity(src))
        odir = daten / "diar2" / "output" / name
        for ext in (".txt", ".srt", ".json", ".hoerliste.txt", ".run.json"):
            assert (odir / f"{name}{ext}").is_file(), f"fehlt: {name}{ext}"
        run = json.loads((odir / f"{name}.run.json").read_text("utf-8"))
        assert run["status"] == "teilweise (nur-transkript)"
        assert run["params"]["mock_transkript"] is True
        # Unveraenderter Zweitlauf: keine Neuberechnung (Instrumentierung).
        r2 = subprocess.run([sys.executable, str(APP), "kette", str(src),
                             "--mock-transkript", str(mock), "--nur-transkript"],
                            capture_output=True, text=True)
        assert r2.returncode == 0, r2.stderr
        run2 = json.loads((odir / f"{name}.run.json").read_text("utf-8"))
        assert run2["schritte"] == {"asr": "skip", "diar": "skip"}
    finally:
        os.environ.pop("OHPIPE_DATA", None)
