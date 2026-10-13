#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut das versionierte Windows-Paket (ZIP + SHA256).

Baut aus dem Projektroot: nur versendbare Dateien (kein .venv, keine
Laufzeit, keine Daten/Modelle/Ergebnisse). Schreibt
<ablage>/ohpipe-mini-windows-<VERSION>.zip und .sha256 dazu.
Aufruf: python scripts/build_paket.py [--ablage PFAD]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATEIEN = [
    "VERSION", "README.md", "LICENSE", "CITATION.cff", "CHANGELOG.md",
    "CONTRIBUTING.md", "SECURITY.md", "START-HIER.txt", ".gitignore",
]
ORDNER = ["app", "bin", "scripts", "tests", "docs", "vendor", ".github"]
# Diese Pfade kommen nie ins Paket (Umgebung, Geheimnisse, Laufzeit, Daten).
AUSGESCHLOSSEN = {".venv", "runtime", "__pycache__", ".pytest_cache",
                  ".DS_Store", ".hf_token"}


def sammeln() -> list[Path]:
    pfade = [ROOT / d for d in DATEIEN]
    for ordner in ORDNER:
        for p in sorted((ROOT / ordner).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if any(teil in AUSGESCHLOSSEN or teil.endswith((".pyc", ".pyo"))
                   for teil in rel.parts):
                continue
            if rel.suffix == ".wav" and rel != Path("tests/data/sprachclip.wav"):
                continue
            pfade.append(p)
    for p in pfade:
        if not p.is_file():
            raise SystemExit(f"fehlt im Paket: {p.relative_to(ROOT)}")
    return pfade


def main() -> int:
    ap = argparse.ArgumentParser(description="Baut ZIP + SHA256.")
    ap.add_argument("--ablage", default=None)
    args = ap.parse_args()
    version = (ROOT / "VERSION").read_text("utf-8").strip()
    ablage = Path(args.ablage) if args.ablage else ROOT.parent
    ablage.mkdir(parents=True, exist_ok=True)
    zip_pfad = ablage / f"ohpipe-mini-windows-{version}.zip"
    with zipfile.ZipFile(zip_pfad, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sammeln():
            z.write(p, f"ohpipe-mini-windows-{version}/{p.relative_to(ROOT)}")
    digest = hashlib.sha256(zip_pfad.read_bytes()).hexdigest()
    (ablage / f"{zip_pfad.name}.sha256").write_text(f"{digest}  {zip_pfad.name}\n")
    kb = zip_pfad.stat().st_size / 1024
    print(f"Paket: {zip_pfad} ({kb:.0f} KB)\nSHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
