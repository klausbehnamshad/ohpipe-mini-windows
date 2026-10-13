"""Nutzerselbsttest mit echter Verarbeitung (kein Mock).

Laeuft mit der privaten Laufzeit (siehe tests/smoke.cmd): kurze
mitgelieferte Sprachaufnahme (tests/data/sprachclip.wav, 2 Stimmen) wird
tatsaechlich transkribiert und per Diarisierung getrennt. Erfolg heisst:
Status fertig, echte Segmente, zwei Sprecher, Schluesselwoerter gefunden.

Exitcodes: 0 bestanden; 1 echte Verarbeitung ungenuegend;
2 Einrichtung unvollstaendig (mit konkretem Hinweis, kein Absturz).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app" / "ohpipe.py"
CLIP = ROOT / "tests" / "data" / "sprachclip.wav"
SCHLUESSEL = ["dorf", "schule", "fabrik", "gespraech", "lehre",
              "bauernhof", "stadtrand", "erinnerungen"]

sys.path.insert(0, str(ROOT / "app"))
import ohpipe  # noqa: E402


def fehler_setup(msg: str) -> int:
    print(f"SELBSTTEST: Einrichtung unvollstaendig: {msg}", file=sys.stderr)
    print("Bitte Setup ausfuehren: "
          "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Install.ps1",
          file=sys.stderr)
    return 2


def main() -> int:
    if not CLIP.is_file():
        print(f"SELBSTTEST: Sprachclip fehlt ({CLIP}). Paket unvollstaendig.",
              file=sys.stderr)
        return 2
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return fehler_setup("faster-whisper nicht installiert (private Laufzeit unvollstaendig).")
    cfg = ohpipe.models_config()
    profil = cfg["profiles"]["standard"]
    asr_dir = ohpipe.data_root() / "modelle" / "asr" / profil["asr_model"]
    if not (asr_dir.is_dir() and any(asr_dir.iterdir())):
        return fehler_setup(f"ASR-Modell fehlt ({asr_dir}). Modelle laden (Setup).")
    import os
    diar_dir = Path(os.environ.get("OHPIPE_DIAR_MODEL",
                                   str(ohpipe.data_root() / "modelle" / "diar")))
    if not (diar_dir.is_dir() and any(diar_dir.iterdir())):
        return fehler_setup(f"Diarisierungsmodell fehlt ({diar_dir}). Modelle laden (Setup).")
    print(f"SELBSTTEST: echte Verarbeitung von {CLIP.name} "
          f"(Modell {profil['asr_model']}, CPU) ...")
    r = subprocess.run([sys.executable, str(APP), "kette", str(CLIP)],
                       capture_output=True, text=True)
    print(r.stdout)
    print(r.stderr, file=sys.stderr)
    if r.returncode == 4:
        print("SELBSTTEST NICHT BESTANDEN: Transkript erhalten, aber Sprechertrennung "
              "fehlgeschlagen (Exitcode 4). Diagnose: oh-diagnose.", file=sys.stderr)
        return 1
    if r.returncode != 0:
        print(f"SELBSTTEST NICHT BESTANDEN (Exitcode {r.returncode}).", file=sys.stderr)
        return 1
    name = ohpipe.interview_id(CLIP, ohpipe.file_identity(CLIP))
    odir = ohpipe.out_dir_for(name)
    for ext in (".txt", ".srt", ".json", ".hoerliste.txt", ".run.json"):
        if not (odir / f"{name}{ext}").is_file():
            print(f"SELBSTTEST NICHT BESTANDEN: {name}{ext} fehlt.", file=sys.stderr)
            return 1
    data = json.loads((odir / f"{name}.json").read_text("utf-8"))
    run = json.loads((odir / f"{name}.run.json").read_text("utf-8"))
    segs = data.get("segments", [])
    text = " ".join(s.get("text", "") for s in segs).lower()
    sprecher = {s.get("speaker") for s in segs}
    treffer = [w for w in SCHLUESSEL if w in text]
    print(f"SELBSTTEST: {len(segs)} Segmente, Sprecher {sorted(sprecher)}, "
          f"Schluesselwoerter {len(treffer)}/{len(SCHLUESSEL)}, Status {run.get('status')}.")
    probleme = []
    if run.get("status") != "fertig":
        probleme.append(f"Status {run.get('status')!r} statt 'fertig'")
    if len(segs) < 4:
        probleme.append(f"nur {len(segs)} Segmente (erwartet >= 4)")
    if len(sprecher) < 2 or any(s in (None, "SPK_??") for s in sprecher):
        probleme.append(f"Sprecher unvollstaendig ({sorted(sprecher)})")
    if any("diarisierung-fehlgeschlagen" in s.get("flags", []) for s in segs):
        probleme.append("Sprecherfehler-Kennzeichnung im Ergebnis")
    if len(treffer) < 3:
        probleme.append(f"nur {len(treffer)} Schluesselwoerter erkannt")
    if probleme:
        print("SELBSTTEST NICHT BESTANDEN:", file=sys.stderr)
        for p in probleme:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"SELBSTTEST OK (echte ASR + Diarisierung): {odir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
