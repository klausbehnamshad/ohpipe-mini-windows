#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Laedt ASR- und Diarisierungsmodelle mit festen Revisionen (Setup-Schritt).

Aufruf aus scripts\\Install.ps1 mit dem privaten Python; nichts wird zur
Laufzeit unbemerkt nachgeladen (app/ohpipe.py arbeitet strikt offline).
Lizenz-/Freigabebedingungen stehen vor dem Download; der Token (nur fuer den
freigabepflichtigen Erst-Download noetig) wird nie gespeichert.
Exitcodes: 0 ok, 2 Fehler mit Einrichtungshinweis.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def daten_root() -> Path:
    override = os.environ.get("OHPIPE_DATA")
    if override:
        return Path(override)
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / "Downloads" / "ohpipe-mini"


def groesse_mb(repo: str, revision: str, token: str | None) -> str:
    try:
        from huggingface_hub import model_info
        info = model_info(repo, revision=revision, token=token)
        total = sum(getattr(s, "size", 0) or 0 for s in (info.siblings or []))
        if total > 0:
            return f"ca. {total / 1e6:.0f} MB"
    except Exception:
        pass
    return "wird beim Download gemessen"


def laden(repo: str, revision: str, ziel: Path, token: str | None) -> int:
    from huggingface_hub import snapshot_download
    print(f"  {repo} @ {revision[:12]} -> {ziel} ({groesse_mb(repo, revision, token)})")
    snapshot_download(repo_id=repo, revision=revision, local_dir=str(ziel),
                      token=token, max_workers=4)
    dateien = [p for p in ziel.rglob("*") if p.is_file()]
    if not dateien:
        raise RuntimeError(f"Leere Modellablage {ziel} — zaehlt nicht als eingerichtet.")
    mb = sum(p.stat().st_size for p in dateien) / 1e6
    print(f"  ok: {len(dateien)} Dateien, {mb:.0f} MB.")
    return len(dateien)


def main() -> int:
    ap = argparse.ArgumentParser(description="ohpipe-mini Modell-Setup (einmalig, mit Netz).")
    ap.add_argument("--daten", default=None)
    ap.add_argument("--token", default=None, help="HF-Token nur fuer freigabepflichtigen Download")
    ap.add_argument("--extra-repo", action="append", default=[],
                    help="Zusaetzliches Repo (repo[:revision]) in modelle/extra laden")
    args = ap.parse_args()
    try:
        from huggingface_hub import __version__ as _hhv  # noqa: F401
    except ImportError:
        print("Fehler: huggingface_hub fehlt. Erst Python-Pakete einrichten.", file=sys.stderr)
        return 2
    cfg = json.loads((ROOT / "app" / "models.json").read_text("utf-8"))
    daten = Path(args.daten) if args.daten else daten_root()
    asr_ziel = daten / "modelle" / "asr"
    diar_ziel = daten / "modelle" / "diar"
    bericht: dict = {"asr": {}, "diar": {}}
    try:
        print("Schritt 1/2: Spracherkennung (frei, Systran CTranslate2-Revisionen) ...")
        for name, m in sorted(cfg["asr"]["modelle"].items()):
            n = laden(m["repo"], m["revision"], asr_ziel / name, None)
            bericht["asr"][name] = {"repo": m["repo"], "revision": m["revision"], "dateien": n}
        print("Schritt 2/2: Sprechertrennung (freigabepflichtig, pyannote) ...")
        print("  Bedingungen: https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("  Dort 'Agree and access repository' bestaetigen; der Token gilt nur")
        print("  fuer diesen Download, wird nie gespeichert, danach ist alles offline.")
        token = args.token or os.environ.get("HF_TOKEN")
        if not token:
            try:
                token = getpass.getpass("  HF-Token (Eingabe unsichtbar, Enter = ohne versuchen): ")
            except (EOFError, KeyboardInterrupt):
                token = None
            token = (token or "").strip() or None
        diar = cfg["diar"]
        try:
            n = laden(diar["repo"], diar["revision"], diar_ziel, token)
        except Exception as e:
            print(f"Fehler: Diarisierungs-Download gescheitert ({e}).", file=sys.stderr)
            print("Hinweis: Freigabe auf der Modellseite bestaetigen und gueltigen Token angeben.",
                  file=sys.stderr)
            return 2
        bericht["diar"]["pipeline"] = {"repo": diar["repo"], "revision": diar["revision"],
                                       "dateien": n}
        n = laden(diar["seg_repo"], diar["seg_revision"], daten / "modelle" / "extra" /
                  diar["seg_repo"].split("/")[-1], token)
        bericht["diar"]["segmentierung"] = {"repo": diar["seg_repo"],
                                            "revision": diar["seg_revision"], "dateien": n}
        # Schritt 2b: alle von der Pipeline referenzierten Gewichte in den
        # HF-Cache vorabladen, damit from_pretrained(config.yaml) spaeter
        # offline funktioniert (einmaliges Laden, kein Unbemerkt-Download).
        print("Schritt 2b: Pipeline einmal laden (Cache-Vorabladung, offline-Nachweis) ...")
        try:
            import torch  # noqa: F401
            from pyannote.audio import Pipeline
            _cfg = diar_ziel / "config.yaml"
            _pl = Pipeline.from_pretrained(
                str(_cfg if _cfg.is_file() else diar_ziel), use_auth_token=token)
            del _pl
            print("  ok: Pipeline laedt aus lokaler Ablage + Cache.")
            bericht["diar"]["offline_ladbar"] = True
        except Exception as e:
            print(f"Fehler: Pipeline laedt nicht ({e}).", file=sys.stderr)
            print("Hinweis: Setup erneut starten; notfalls --extra-repo fuer fehlende "
                  "Gewichte nutzen (Fehlermeldung nennt das Repo).", file=sys.stderr)
            return 2
        for extra in args.extra_repo:
            repo, _, rev = extra.partition(":")
            ziel = daten / "modelle" / "extra" / repo.split("/")[-1]
            n = laden(repo, rev or "main", ziel, token)
            bericht.setdefault("extra", {})[repo] = {"revision": rev or "main", "dateien": n}
    except Exception as e:
        print(f"Fehler beim Modell-Download: {e}", file=sys.stderr)
        print("Unvollstaendige Modelle zaehlen nicht als eingerichtet; Setup erneut starten.",
              file=sys.stderr)
        return 2
    bericht["token_gespeichert"] = False
    state_pfad = ROOT / "runtime" / "state.json"
    state = {}
    if state_pfad.is_file():
        try:
            state = json.loads(state_pfad.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {}
    state["modelle"] = bericht
    state_pfad.parent.mkdir(parents=True, exist_ok=True)
    state_pfad.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Modelle bereit unter {daten / 'modelle'} (Revisionen in runtime/state.json).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
