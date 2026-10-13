#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ohpipe-mini Windows (Neuimplementierung; Version siehe VERSION-Datei).

Mac-Methode (MLX/Nemotron) ist auf Windows x64 nicht lauffaehig; dieser Kern
nutzt FFmpeg-Import + faster-whisper (CPU/INT8) + pyannote lokal. Abweichungen
stehen in docs/OFFENE-PUNKTE.md. Kern braucht weder Ollama noch LLM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

# Anwendungsordner fest einbinden: Die private Windows-Laufzeit (Embed)
# startet isoliert (kein Skriptordner, keine Umgebung im Modulpfad).
# Ohne diese Zeile findet sie ohext/diar_adapter/diar2_merge nicht —
# unabhaengig vom Arbeitsverzeichnis und von fremden Installationen.
sys.path.insert(0, str(Path(__file__).resolve().parent))

def _app_version() -> str:
    try:
        return (Path(__file__).resolve().parent.parent / "VERSION").read_text("utf-8").strip()
    except OSError:
        return "0.3.0"


APP_VERSION = _app_version()
# Format 2: Woerter mit Zeitquelle, Merge-Saetze, Rollenvorschlag, RTTM.
# Format 1 (Segmente ohne Woerter) wird lesend weiter unterstuetzt (Migration).
JSON_FORMAT = 2

# Dokumentierte Exitcodes (auch in --help und Handbuch).
EXIT_OK = 0
EXIT_FEHLER = 2          # Eingabe ungueltig / Verarbeitung gescheitert
EXIT_BELEGT = 3          # Eingabe wird bereits verarbeitet (Lock)
EXIT_TEILWEISE = 4       # Transkript erhalten, Sprechertrennung fehlgeschlagen

# Wiederaufnahmefaehige Status in NAME.run.json.
STATUS_FERTIG = "fertig"
STATUS_NUR_TRANSKRIPT = "teilweise (nur-transkript)"
STATUS_DIAR_FEHLER = "teilweise (diarisierung-fehlgeschlagen)"
# Status, bei denen kein Schritt wiederholt werden muss (Ausgaben pruefen!).
STATUS_ABGESCHLOSSEN = frozenset({STATUS_FERTIG, STATUS_NUR_TRANSKRIPT})

WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *{f"com{i}" for i in range(1, 10)},
    *{f"lpt{i}" for i in range(1, 10)},
}

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma", ".aiff", ".aif"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv"}


def app_root() -> Path:
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    override = os.environ.get("OHPIPE_DATA")
    if override:
        return Path(override)
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / "Downloads" / "ohpipe-mini"


def out_dir_for(name: str) -> Path:
    return data_root() / "diar2" / "output" / name


def workdir_for(name: str) -> Path:
    return data_root() / "diar2" / ".work" / name


def interview_id(src: Path, file_id: dict) -> str:
    """Eindeutige Interviewidentitaet: Stamm + kurzer Inhalts-Hash.

    Verschiedene Dateien gleichen Namens erhalten so verschiedene
    Ergebnisordner; identische Inhalte teilen sich zu Recht einen Ordner.
    """
    return f"{safe_name(src.stem)}--{file_id['sha256'][:8]}"


def file_identity(path: Path) -> dict:
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size,
            "mtime": path.stat().st_mtime}


def tool_path(name: str) -> str:
    """Findet FFmpeg/FFprobe aus der privaten Einrichtung, sonst aus PATH.

    Der Programmprozess findet die Medienwerkzeuge damit unabhaengig von
    einer vorhandenen Systeminstallation (Setup legt runtime/ffmpeg an).
    """
    import shutil
    exe = name + ".exe" if os.name == "nt" else name
    privat = app_root() / "runtime" / "ffmpeg" / "bin" / exe
    if privat.is_file():
        return str(privat)
    gefunden = shutil.which(name) or shutil.which(exe)
    return gefunden or name


def models_config() -> dict:
    return json.loads((app_root() / "app" / "models.json").read_text("utf-8"))


def model_state(cfg: dict) -> dict:
    """Revisionen, die in die Wiederaufnahmeentscheidung eingehen."""
    return {"asr": cfg.get("asr"), "diar": cfg.get("diar"),
            "profile": cfg.get("profiles")}


def resolve_asr_model(cfg: dict, model_name: str) -> str:
    """Lokaler Modellordner hat Vorrang; kurzer Name nur als Rueckfall."""
    lokal = data_root() / "modelle" / "asr" / model_name
    if lokal.is_dir() and any(lokal.iterdir()):
        return str(lokal)
    return model_name


def safe_name(stem: str) -> str:
    cleaned = "".join(c if (c.isalnum() or c in ("-", "_", ".", " ")) else "_" for c in stem.strip())
    cleaned = cleaned.strip().rstrip(".") or "aufnahme"
    if cleaned.lower() in WINDOWS_RESERVED:
        cleaned = "_" + cleaned
    return cleaned[:120]


def sha256_file(path: Path, limit_mb: int = 2048) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def fmt_ts_txt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"[{h:02d}:{m:02d}:{s:04.1f}]"


def atomic_write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(tmp, mode, encoding=None if isinstance(data, bytes) else "utf-8") as f:
        f.write(data)
    os.replace(tmp, path)


def run_cmd(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def probe_media(path: Path, ffmpeg: str | None = None, ffprobe: str | None = None) -> dict:
    """Prueft Dateiinhalt (nicht nur Endung). Verstaendliche Fehler."""
    if not path.is_file():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Leere Datei (0 Byte): {path}")
    ext = path.suffix.lower()
    if ext not in AUDIO_EXTS | VIDEO_EXTS:
        raise ValueError(f"Endung {ext!r} wird nicht unterstuetzt: {path}")
    ffprobe = ffprobe or tool_path("ffprobe")
    r = run_cmd([ffprobe, "-v", "error", "-show_entries",
                 "stream=index,codec_type,codec_name", "-of", "json", str(path)])
    if r.returncode != 0:
        raise ValueError(f"Datei ist beschaedigt oder unlesbar: {path}\n{r.stderr.strip()[:400]}")
    try:
        info = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        raise ValueError(f"Unbekanntes Dateiformat (kein Mediainhalt): {path}")
    streams = (info.get("streams") or [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio:
        raise ValueError(f"Keine Audiospur gefunden (Video ohne Ton?): {path}")
    return {"streams": streams, "audio_tracks": len(audio),
            "audio_codecs": [s.get("codec_name", "?") for s in audio]}


def to_work_wav(src: Path, workdir: Path, ffmpeg: str | None = None,
                track: int = 0) -> tuple[Path, float]:
    """Wandelt Original in 16 kHz Mono-WAV um. Original bleibt unveraendert."""
    ffmpeg = ffmpeg or tool_path("ffmpeg")
    ffprobe = tool_path("ffprobe")
    workdir.mkdir(parents=True, exist_ok=True)
    wav = workdir / (safe_name(src.stem) + ".16k.wav")
    r = run_cmd([ffmpeg, "-y", "-v", "error", "-i", str(src),
                 "-map", f"0:a:{track}", "-ac", "1", "-ar", "16000",
                 "-c:a", "pcm_s16le", str(wav)])
    if r.returncode != 0 or not wav.is_file():
        raise RuntimeError(f"FFmpeg-Import fehlgeschlagen: {r.stderr.strip()[:500]}")
    d = run_cmd([ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(wav)])
    try:
        duration = float((d.stdout or "0").strip())
    except ValueError:
        duration = 0.0
    return wav, duration


def transcribe(wav: Path, lang: str, model: str) -> list[dict]:
    """Lokale Transkription via faster-whisper (CPU/INT8). Kein Netzwerk."""
    for k, v in {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                 "HF_HUB_DISABLE_TELEMETRY": "1"}.items():
        os.environ.setdefault(k, v)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "Transkriptionsmodell nicht eingerichtet (faster-whisper fehlt). "
            "Bitte Setup ausfuehren (scripts\\Install.ps1); es wird nichts "
            "automatisch nachgeladen.")
    modell_pfad = resolve_asr_model(models_config(), model)
    try:
        m = WhisperModel(modell_pfad, device="cpu", compute_type="int8")
    except Exception as e:
        raise RuntimeError(
            f"Transkriptionsmodell {model!r} nicht ladbar ({e}). Bitte Setup "
            f"erneut ausfuehren (Modelle laden); fehlende Dateien werden "
            f"offline mit Einrichtungshinweis gemeldet.")
    try:
        seg_iter, info = m.transcribe(str(wav), language=None if lang == "auto" else lang,
                                      vad_filter=True, word_timestamps=True)
    except TypeError:
        # Aeltere Engine ohne Wortzeiten: Segmente ohne Woerter (Fallback).
        seg_iter, info = m.transcribe(str(wav), language=None if lang == "auto" else lang,
                                      vad_filter=True)
    out = []
    detected = None
    for i, s in enumerate(seg_iter):
        woerter = []
        for w in getattr(s, "words", None) or []:
            woerter.append({"word": w.word.strip(), "start": float(w.start),
                            "end": float(w.end),
                            "score": getattr(w, "probability", None)})
        out.append({"id": f"seg{i+1:04d}", "start": float(s.start),
                    "end": float(s.end), "text": s.text.strip(),
                    "speaker": None, "flags": [], "words": woerter})
    detected = getattr(info, "language", lang)
    for s in out:
        s["lang"] = detected
    return out


def diarize_turns(wav: Path, n_speakers: int | None,
                  diar_model_dir: Path) -> list[tuple]:
    """Sprecherintervalle (start, ende, SPK_xx) aus lokalem Modellordner.

    Laedt die Pipeline aus der lokalen config.yaml (kein Hub-Zugriff zur
    Laufzeit); faellt nur darauf zurueck, den Ordner direkt zu nennen.
    """
    for k, v in {"HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
                 "PYANNOTE_METRICS_ENABLED": "false"}.items():
        os.environ.setdefault(k, v)
    if not diar_model_dir.is_dir():
        raise RuntimeError(
            "Diarisierungsmodell fehlt. Bitte Setup ausfuehren; "
            "offline ohne Modell abgebrochen.")
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        raise RuntimeError("pyannote.audio ist nicht installiert (Setup unvollstaendig).")
    config = diar_model_dir / "config.yaml"
    quelle = str(config if config.is_file() else diar_model_dir)
    pipeline = Pipeline.from_pretrained(quelle)
    kwargs = {}
    if n_speakers:
        kwargs["num_speakers"] = n_speakers
    diar = pipeline(str(wav), **kwargs)
    turns: list[tuple[float, float, str]] = []
    for turn, _, speaker in diar.itertracks(yield_label=True):
        turns.append((float(turn.start), float(turn.end), str(speaker)))
    labels = sorted({t[2] for t in turns})
    mapping = {old: f"SPK_{i+1:02d}" for i, old in enumerate(labels)}
    return [(a, b, mapping[lab]) for a, b, lab in turns]


def diarize(wav: Path, segments: list[dict], n_speakers: int | None,
            diar_model_dir: Path) -> list[dict]:
    """Segment-Sprecher aus Intervallen (Kompatibilitaet; nutzt diarize_turns)."""
    return assign_segments_from_turns(
        segments, diarize_turns(wav, n_speakers, diar_model_dir))


def assign_segments_from_turns(segments: list[dict],
                               turns: list[tuple]) -> list[dict]:
    """Ordnet Segmenten Sprecher aus Intervallen zu (Ueberlappungsmaximum)."""

    def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    for s in segments:
        scores: dict[str, float] = {}
        for (t0, t1, lab) in turns:
            ov = overlap(s["start"], s["end"], t0, t1)
            if ov > 0:
                scores[lab] = scores.get(lab, 0.0) + ov
        if not scores:
            s["speaker"] = "SPK_01"
            s["flags"] = sorted(set(s.get("flags", [])) | {"pruefen:keine-sprecherabdeckung"})
            continue
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        s["speaker"] = ranked[0][0]
        flags = set(s.get("flags", []))
        if len(ranked) > 1 and ranked[1][1] >= 0.4 * ranked[0][1]:
            flags.add("heuristik:ueberlappung-oder-unsicher")
        if s["end"] - s["start"] < 1.0:
            flags.add("heuristik:sehr-kurzer-turn-pruefen")
        if len(s.get("text", "").split()) < 4:
            flags.add("heuristik:kurz-einwurf")
        s["flags"] = sorted(flags)
    return segments


KERN_DATEIEN = (".txt", ".srt", ".json", ".hoerliste.txt")


def kern_outputs_complete(odir: Path, name: str) -> bool:
    return all((odir / f"{name}{ext}").is_file() for ext in KERN_DATEIEN)


def voll_outputs_complete(name: str) -> bool:
    """Prueft, ob die --voll-Erweiterung fuer NAME vollstaendig vorliegt."""
    try:
        import ohext
    except ImportError:
        return False
    mdir = ohext.meta_dir(name)
    return all((mdir / f"{name}{ext}").is_file()
               for ext in (".imm.draft.json", ".imm.provenance.json",
                           ".entwurf.json", ".pii.json", ".pruefliste.txt"))


def asr_cache_path(workdir: Path) -> Path:
    return workdir / "asr-cache.json"


def load_asr_cache(workdir: Path, file_id: dict, params: dict,
                   asr_state: dict) -> list[dict] | None:
    """Gibt zwischengespeicherte ASR-Segmente zurueck (oder None).

    Abgeschlossene ASR wird unabhaengig vom Diarisierungserfolg
    zwischengespeichert: Nach einem Sprecherfehler muss nur der
    fehlgeschlagene Schritt wiederholt werden.
    """
    p = asr_cache_path(workdir)
    if not p.is_file():
        return None
    try:
        cached = json.loads(p.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if (cached.get("input") == file_id
            and cached.get("params") == params
            and cached.get("asr") == asr_state
            and isinstance(cached.get("segments"), list)
            and cached["segments"]):
        return cached["segments"]
    return None


def save_asr_cache(workdir: Path, file_id: dict, params: dict,
                   asr_state: dict, segments: list[dict]) -> None:
    atomic_write(asr_cache_path(workdir),
                 json.dumps({"input": file_id, "params": params,
                             "asr": asr_state, "segments": segments},
                            ensure_ascii=False) + "\n")


def load_kern_segments(odir: Path, name: str) -> list[dict] | None:
    """Liest erhaltene Segmente aus einem frueheren Lauf (Transkript bleibt)."""
    jpath = odir / f"{name}.json"
    if not jpath.is_file():
        return None
    try:
        data = json.loads(jpath.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    segs = data.get("segments")
    return segs if isinstance(segs, list) and segs else None


def backup_outputs(odir: Path, name: str) -> None:
    """Sichert vorhandene (moeglicherweise manuell korrigierte) Ergebnisse
    vor dem Ueberschreiben durch eine Neuberechnung."""
    for ext in (*KERN_DATEIEN, ".run.json"):
        src = odir / f"{name}{ext}"
        if src.is_file():
            ziel = odir / f"{name}{ext}.bak"
            try:
                ziel.write_bytes(src.read_bytes())
            except OSError:
                pass


def write_txt(segments: list[dict]) -> str:
    lines = []
    for s in segments:
        spk = s.get("speaker") or "SPK_??"
        lines.append(f'{fmt_ts_txt(s["start"])} {spk}: {s["text"]}')
        for f in s.get("flags", []):
            if f.startswith("pruefen:") or f.startswith("heuristik:"):
                lines.append(f"  [Hinweis: {f}]")
                break
    return "\n".join(lines).rstrip() + "\n"


def write_srt(segments: list[dict]) -> str:
    out = []
    for i, s in enumerate(segments, 1):
        spk = s.get("speaker") or "SPK_??"
        text = s["text"].replace("\n", " ")
        out.append(f"{i}\n{fmt_ts(s['start'])} --> {fmt_ts(s['end'])}\n{spk}: {text}\n")
    return "\n".join(out)


def write_json(name: str, segments: list[dict], meta: dict) -> dict:
    for s in segments:
        assert s["end"] >= s["start"], "Segmentende vor Segmentanfang"
        assert s["end"] <= meta["duration"] + 1.0, "Segment ausserhalb der Aufnahme"
    out = {"format": "ohpipe-mini-windows", "format_version": JSON_FORMAT,
           "name": name, "language": meta.get("language", "de"),
           "roles": {}, "role_status": "unbestaetigt",
           "segments": segments, "tech": meta.get("tech", {})}
    # Format 2 (Wortebene aus diar2_merge); fehlt bei reiner Transkription
    # und bei alten Format-1-Ergebnissen (lesend weiter unterstuetzt).
    for schluessel in ("words", "sentences", "turns", "alignment",
                       "alignment_hinweis", "merge", "rollenvorschlag"):
        if schluessel in meta:
            out[schluessel] = meta[schluessel]
    return out


def hoerliste(segments: list[dict]) -> str:
    cands = []
    for i, s in enumerate(segments):
        for f in s.get("flags", []):
            if f.startswith("pruefen:") or f.startswith("heuristik:"):
                cands.append((i, s, f))
                break
    cands.sort(key=lambda t: (t[1]["end"] - t[1]["start"]), reverse=True)
    lines = ["Pruefstellen (laengste zuerst) — erste Minute zur Rollenkontrolle pruefen:",
             ""]
    for n, (i, s, f) in enumerate(cands, 1):
        lines.append(f'{n:3d}. {s["start"]:07.1f} - {s["end"]:07.1f} '
                     f'({s["end"]-s["start"]:4.1f} s) {s.get("speaker","?")}: {f}: '
                     f'{s["text"][:90]}')
    if not cands:
        lines.append("Keine unsicheren Stellen markiert.")
    return "\n".join(lines) + "\n"


def _read_run(run_path: Path) -> dict | None:
    if not run_path.is_file():
        return None
    try:
        old = json.loads(run_path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return old if isinstance(old, dict) else None


def cmd_kette(args) -> int:
    src = Path(args.datei)
    t0 = time.time()
    lock_acquired = False
    if bool(getattr(args, "nur_transkript", False)) and bool(getattr(args, "voll", False)):
        print("Fehler: --nur-transkript und --voll schliessen sich aus "
              "(--voll braucht die Sprecherzuordnung).", file=sys.stderr)
        return EXIT_FEHLER
    try:
        media = probe_media(src)
    except (FileNotFoundError, ValueError) as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return EXIT_FEHLER
    if media["audio_tracks"] > 1 and args.spur is None:
        print(f"Hinweis: {media['audio_tracks']} Audiospuren gefunden "
              f"({', '.join(media['audio_codecs'])}); verwende Spur 0. "
              f"Mit --spur N andere Spur waehlen.")
    track = args.spur or 0
    if track >= media["audio_tracks"]:
        print(f"Fehler: Spur {track} gibt es nicht "
              f"({media['audio_tracks']} Spuren).", file=sys.stderr)
        return EXIT_FEHLER
    # Eindeutige Identitaet VOR dem Ordner: gleiche Namen, andere Inhalte
    # erhalten eigene Ergebnisordner.
    file_id = file_identity(src)
    name = interview_id(src, file_id)
    odir = out_dir_for(name)
    workdir = odir.parent.parent / ".work" / name
    workdir.mkdir(parents=True, exist_ok=True)
    lock = odir / ".lock"
    schritte: dict[str, str] = {}
    try:
        odir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("ascii"))
            finally:
                os.close(fd)
            lock_acquired = True
        except FileExistsError:
            besitzer = ""
            try:
                besitzer = f" (Prozess {lock.read_text('utf-8').strip()})"
            except OSError:
                pass
            print(f"Fehler: {name} wird bereits verarbeitet (Lock){besitzer}.",
                  file=sys.stderr)
            return EXIT_BELEGT
        models_cfg = models_config()
        profile = models_cfg["profiles"].get(args.profil, models_cfg["profiles"]["standard"])
        zustand = model_state(models_cfg)
        params = {"sprache": args.sprache, "sprecher": args.sprecher,
                  "profil": args.profil, "spur": track,
                  "nur_transkript": bool(args.nur_transkript),
                  "mock_transkript": bool(getattr(args, "mock_transkript", None))}
        asr_params = {"sprache": args.sprache, "profil": args.profil, "spur": track}
        asr_stand = {"repo": (zustand.get("asr") or {}).get("modelle",
                     {}).get(profile["asr_model"]) if isinstance(zustand.get("asr"), dict) else None,
                     "modell": profile["asr_model"]}
        run_path = odir / f"{name}.run.json"
        will_voll = bool(getattr(args, "voll", False))
        will_nur = bool(args.nur_transkript)
        # --- Wiederaufnahme: unveraenderte Zweitlaeufe starten keine Inferenz.
        # Gilt fuer Kern UND Vollkette, auch bei reiner Transkription. ---
        if not bool(getattr(args, "neu", False)):
            old = _read_run(run_path)
            if old is not None and old.get("input") == file_id:
                if old.get("params") != params:
                    print("Parameter geaendert — betroffene Schritte werden neu berechnet "
                          "(vorhandene Ergebnisse werden nach .bak gesichert).")
                    backup_outputs(odir, name)
                elif old.get("modelle") != zustand:
                    print("Modellrevision geaendert — Inferenz wird neu gestartet "
                          "(vorhandene Ergebnisse werden nach .bak gesichert).")
                    backup_outputs(odir, name)
                elif (old.get("status") in STATUS_ABGESCHLOSSEN
                        and kern_outputs_complete(odir, name)
                        and (old.get("status") != STATUS_FERTIG
                             or (odir / f"{name}.rttm").is_file())
                        and (will_nur or old.get("status") == STATUS_FERTIG
                             or load_kern_segments(odir, name) is not None)):
                    if will_nur or old.get("status") == STATUS_FERTIG:
                        schritte = {"asr": "skip", "diar": "skip"}
                        if will_voll:
                            if voll_outputs_complete(name):
                                print(f"Unveraendert — {name} ist fertig (Kern + Vollkette), "
                                      f"keine Inferenz neu gestartet.")
                                print(f"Ergebnisordner: {odir}")
                                _write_run(run_path, name, file_id, params, zustand,
                                           old, schritte, t0)
                                return EXIT_OK
                            print("Kern unveraendert — nur die Vollkette wird ergaenzt "
                                  "(keine Inferenz neu gestartet).")
                            import ohext
                            rc = ohext.voll_chain(name)
                            _write_run(run_path, name, file_id, params, zustand,
                                       old, {"asr": "skip", "diar": "skip",
                                             "voll": "neu" if rc == 0 else "fehler"},
                                       t0, voll=(rc == 0))
                            print(f"Ergebnisordner: {odir}")
                            return rc
                        print(f"Unveraendert — {name} ist {old.get('status')}, "
                              f"keine Inferenz neu gestartet.")
                        print(f"Ergebnisordner: {odir}")
                        _write_run(run_path, name, file_id, params, zustand,
                                   old, schritte, t0)
                        return EXIT_OK
                # Fehlgeschlagene Diarisierung: Transkript erhalten, nur den
                # fehlgeschlagenen Schritt wiederholen (ASR aus Cache/Datei).
                if (not will_nur and old.get("status") == STATUS_DIAR_FEHLER
                        and old.get("params") == params
                        and old.get("modelle") == zustand
                        and kern_outputs_complete(odir, name)):
                    print("Frueherer Lauf: Transkript erhalten, Sprechertrennung offen — "
                          "wiederhole nur die Sprechertrennung (keine neue Transkription).")
                    import ohext  # noqa: F401  (Vollkette erst nach gelungener Diarisierung)
                    wav, duration = to_work_wav(src, workdir, track=track)
                    segments = load_asr_cache(workdir, file_id, asr_params, asr_stand)
                    schritte["asr"] = "cache" if segments is not None else "datei"
                    if segments is None:
                        cached = load_kern_segments(odir, name)
                        segments = [dict(s, speaker=None,
                                         flags=[f for f in s.get("flags", [])
                                                if f != "pruefen:diarisierung-fehlgeschlagen"])
                                    for s in (cached or [])]
                    rc = _diar_export(name, odir, wav, duration,
                                      segments, args, profile, zustand, file_id,
                                      params, schritte, t0, will_voll)
                    return rc
        # --- Frischer Lauf (oder gezielte Neuberechnung) ---
        print(f"Schritt 1/4: Import ({src.name}, Spur {track}) ...")
        wav, duration = to_work_wav(src, workdir, track=track)
        if getattr(args, "mock_transkript", None):
            # Nur Entwicklungs-/Selbsttest; wird nie als ASR-Cache abgelegt
            # und nie mit echter Inferenz verwechselt (params enthalten mock).
            segments = json.loads(Path(args.mock_transkript).read_text("utf-8"))
            schritte["asr"] = "mock"
        else:
            segments = load_asr_cache(workdir, file_id, asr_params, asr_stand)
            if segments is not None:
                print("Schritt 2/4: Transkription aus Zwischenspeicher (keine Inferenz).")
                schritte["asr"] = "cache"
            else:
                segments = _reuse_transcript(odir, name, run_path, file_id,
                                             asr_params, zustand)
                if segments is not None:
                    print("Schritt 2/4: Transkription aus vorhandenem Ergebnis "
                          "(keine Inferenz).")
                    schritte["asr"] = "datei"
                else:
                    print(f"Schritt 2/4: Transkription (Modell {profile['asr_model']}, "
                          f"CPU/INT8) ...")
                    segments = transcribe(wav, args.sprache, profile["asr_model"])
                    schritte["asr"] = "neu"
                    save_asr_cache(workdir, file_id, asr_params, asr_stand, segments)
        if will_nur:
            for s in segments:
                s["speaker"] = "SPK_??"
            schritte["diar"] = "nicht-angefordert"
            return _export_und_run(run_path, name, odir, segments, args, profile,
                                   duration, file_id, params, zustand, schritte, t0,
                                   STATUS_NUR_TRANSKRIPT, EXIT_OK)
        return _diar_export(name, odir, wav, duration, segments, args, profile,
                            zustand, file_id, params, schritte, t0, will_voll)
    except (ValueError, RuntimeError) as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return EXIT_FEHLER
    finally:
        # Nur selbst erworbene Locks entfernen — nie den Lock eines
        # konkurrierenden Prozesses (FileExistsError-Fall).
        if lock_acquired:
            try:
                lock.unlink()
            except OSError:
                pass


def _reuse_transcript(odir: Path, name: str, run_path: Path, file_id: dict,
                      asr_params: dict, zustand: dict) -> list[dict] | None:
    """Nutzt ein erhaltenes Transkript, wenn Eingabe, ASR-Parameter und
    Modellrevisionen unveraendert sind (Upgrade reine Transkription -> voll)."""
    old = _read_run(run_path)
    if old is None or old.get("input") != file_id:
        return None
    if old.get("modelle") != zustand:
        return None
    if old.get("status") not in STATUS_ABGESCHLOSSEN:
        return None
    alte_params = old.get("params") or {}
    if {k: alte_params.get(k) for k in ("sprache", "profil", "spur")} != asr_params:
        return None
    if not kern_outputs_complete(odir, name):
        return None
    return load_kern_segments(odir, name)


def _export_und_run(run_path: Path, name: str, odir: Path, segments: list[dict],
                    args, profile: dict, duration: float, file_id: dict,
                    params: dict, zustand: dict, schritte: dict, t0: float,
                    status: str, exit_code: int, merge_payload: dict | None = None,
                    hoerliste_text: str | None = None,
                    rttm_entries: list | None = None) -> int:
    print("Schritt 4/4: Export (TXT/SRT/JSON/Hoerliste/RTTM) ...")
    vollstaendig = status == STATUS_FERTIG
    meta = {"duration": duration, "language": args.sprache,
            "tech": {"app": APP_VERSION, "profil": args.profil,
                     "asr_model": profile["asr_model"],
                     "asr_revision": ((zustand.get("asr") or {}).get("modelle") or {}).get(
                         profile["asr_model"]),
                     "vollstaendig_mit_sprechern": vollstaendig}}
    if merge_payload:
        meta.update(merge_payload)
    atomic_write(odir / f"{name}.txt", write_txt(segments))
    atomic_write(odir / f"{name}.srt", write_srt(segments))
    atomic_write(odir / f"{name}.json",
                 json.dumps(write_json(name, segments, meta),
                            ensure_ascii=False, indent=2) + "\n")
    atomic_write(odir / f"{name}.hoerliste.txt",
                 hoerliste_text if hoerliste_text is not None else hoerliste(segments))
    if rttm_entries is not None:
        import diar2_merge as _merge
        _merge.write_rttm(odir / f"{name}.rttm",
                           [_merge.Seg(a, b, sp) for a, b, sp in rttm_entries],
                           recording_id=name)
    run = {"name": name, "status": status,
           "input": file_id, "params": params, "modelle": zustand,
           "schritte": schritte,
           "dauer_s": round(time.time() - t0, 1),
           "datum": date.today().isoformat(), "app": APP_VERSION,
           "hinweis": "Neuimplementierung (faster-whisper+pyannote); "
                      "keine exakte Mac-Portierung."}
    atomic_write(run_path, json.dumps(run, ensure_ascii=False, indent=2) + "\n")
    if status == STATUS_FERTIG:
        print("Fertig (mit Sprecherzuordnung).")
    elif status == STATUS_NUR_TRANSKRIPT:
        print("Fertig (ohne Sprecherzuordnung; --nur-transkript).")
    else:
        print("Teilweise fertig: Transkript erhalten, Sprechertrennung "
              "fehlgeschlagen (Exitcode 4). Erneuter Lauf wiederholt nur die "
              "Sprechertrennung.", file=sys.stderr)
    print(f"Ergebnisordner: {odir}")
    return exit_code


def _write_run(run_path: Path, name: str, file_id: dict, params: dict,
               zustand: dict, old: dict, schritte: dict, t0: float,
               voll: bool | None = None) -> None:
    """Aktualisiert run.json bei Wiederaufnahme (Instrumentierung: schritte)."""
    run = dict(old)
    run.update({"name": name, "input": file_id, "params": params,
                "modelle": zustand, "schritte": schritte,
                "dauer_s": round(time.time() - t0, 1),
                "datum": date.today().isoformat(), "app": APP_VERSION})
    if voll is not None:
        run["voll"] = {"status": "fertig" if voll else "fehler",
                       "datum": date.today().isoformat()}
    atomic_write(run_path, json.dumps(run, ensure_ascii=False, indent=2) + "\n")


def _diar_export(name: str, odir: Path, wav: Path, duration: float,
                 segments: list[dict], args, profile: dict, zustand: dict,
                 file_id: dict, params: dict, schritte: dict, t0: float,
                 will_voll: bool) -> int:
    """Sprechertrennung + Export. Bei Fehlschlag: Transkript erhalten,
    dokumentierter Fehlerstatus (Exitcode 4) — die Vollkette darf daraus
    keine vollstaendige erfolgreiche Verarbeitung machen."""
    print("Schritt 3/4: Sprechertrennung (lokal) ...")
    run_path = odir / f"{name}.run.json"
    diar_dir = Path(os.environ.get("OHPIPE_DIAR_MODEL",
                                   str(data_root() / "modelle" / "diar")))
    if not diar_dir.is_dir() or not any(diar_dir.iterdir()):
        return _diar_fehlgeschlagen(
            run_path, name, odir, segments, args, profile, duration,
            file_id, params, zustand, schritte, t0, will_voll,
            f"Diarisierungsmodell fehlt ({diar_dir}). Bitte Setup ausfuehren "
            f"(scripts\\Install.ps1); offline ohne Modell abgebrochen "
            f"(leere Modellablage zaehlt nicht als eingerichtet).")
    try:
        turns = diarize_turns(wav, args.sprecher, diar_dir)
    except RuntimeError as e:
        return _diar_fehlgeschlagen(
            run_path, name, odir, segments, args, profile, duration,
            file_id, params, zustand, schritte, t0, will_voll,
            f"Sprechertrennung fehlgeschlagen: {e}")
    schritte["diar"] = "neu"
    segments = assign_segments_from_turns(segments, turns)
    # Wortebene: Adapter auf diar2_merge (feste Revision, getestete Logik).
    import diar_adapter
    words_data = diar_adapter.build_words_data(segments, args.sprache,
                                               profile["asr_model"])
    schritte["wortzeiten"] = ("geschaetzt" if words_data["alignment"]
                              == diar_adapter.FALLBACK_ALIGNMENT else "echt")
    try:
        merge_result = diar_adapter.run_merge(
            words_data, turns, name, workdir_for(name),
            {"name": name, "profil": args.profil,
             "asr_model": profile["asr_model"]})
    except (OSError, ValueError) as e:
        return _diar_fehlgeschlagen(
            run_path, name, odir, segments, args, profile, duration,
            file_id, params, zustand, schritte, t0, will_voll,
            f"Wortzusammenfuehrung fehlgeschlagen: {e}")
    merged = diar_adapter.sentences_to_segments(merge_result)
    rttm = diar_adapter.smoothed_rttm_entries(merge_result)
    vorschlag = diar_adapter.rollenvorschlag(merge_result)
    erste = vorschlag.get("erste_stimme")
    merge_payload = {"words": merge_result.get("words", []),
                     "sentences": merge_result.get("sentences", []),
                     "turns": merge_result.get("turns", []),
                     "alignment": words_data["alignment"],
                     "merge": {"tool": merge_result.get("tool"),
                               "quelle": "diar2@4ea28ce9736a4de56584c325533c653b1b8e4951",
                               "schwellen": merge_result.get("thresholds", {})},
                     "rollenvorschlag": vorschlag}
    if words_data.get("alignment_hinweis"):
        merge_payload["alignment_hinweis"] = words_data["alignment_hinweis"]
    rc = _export_und_run(run_path, name, odir, merged, args, profile,
                         duration, file_id, params, zustand, schritte, t0,
                         STATUS_FERTIG, EXIT_OK, merge_payload,
                         diar_adapter.review_to_hoerliste(merge_result, erste),
                         rttm)
    if will_voll:
        print("Schritt 5/5: Vollkette (Entwurf, Vorschlaege, PII, Pruefliste) ...")
        import ohext
        vrc = ohext.voll_chain(name)
        old = _read_run(run_path) or {}
        _write_run(run_path, name, file_id, params, zustand, old,
                   {**schritte, "voll": "neu" if vrc == 0 else "fehler"},
                   t0, voll=(vrc == 0))
        return vrc
    return rc


def _diar_fehlgeschlagen(run_path: Path, name: str, odir: Path,
                         segments: list[dict], args, profile: dict,
                         duration: float, file_id: dict, params: dict,
                         zustand: dict, schritte: dict, t0: float,
                         will_voll: bool, meldung: str) -> int:
    print(f"FEHLER: {meldung} Transkript bleibt erhalten; erneute "
          f"Sprecherverarbeitung moeglich.", file=sys.stderr)
    for s in segments:
        s["speaker"] = s.get("speaker") or "SPK_??"
        s["flags"] = sorted(set(s.get("flags", []))
                            | {"pruefen:diarisierung-fehlgeschlagen"})
    schritte["diar"] = "fehler"
    rc = _export_und_run(run_path, name, odir, segments, args, profile,
                         duration, file_id, params, zustand, schritte, t0,
                         STATUS_DIAR_FEHLER, EXIT_TEILWEISE)
    if will_voll:
        print("Die Vollkette entfaellt: Ohne Sprecherzuordnung gibt es keine "
              "vollstaendige erfolgreiche Verarbeitung (Exitcode 4).",
              file=sys.stderr)
    return rc


def cmd_stapel(args) -> int:
    folder = Path(args.ordner) if args.ordner else data_root() / "input"
    if not folder.is_dir():
        print(f"Fehler: Eingabeordner fehlt: {folder}", file=sys.stderr)
        return 2
    pattern = "**/*" if args.rekursiv else "*"
    files = [p for p in folder.glob(pattern)
             if p.is_file() and p.suffix.lower() in AUDIO_EXTS | VIDEO_EXTS]
    ok, skip, fail = [], [], []
    for f in sorted(files):
        sub = argparse.Namespace(datei=str(f), sprache=args.sprache,
                                 sprecher=args.sprecher, profil=args.profil,
                                 spur=None, nur_transkript=False, neu=False,
                                 voll=False, mock_transkript=args.mock_transkript)
        rc = cmd_kette(sub)
        if rc == 0:
            ok.append(str(f))
        else:
            fail.append(str(f))
    print(f"Stapel: {len(ok)} fertig, {len(skip)} uebersprungen, {len(fail)} Fehler.")
    for f in fail:
        print(f"  FEHLER: {f}")
    return 1 if fail else 0


def cmd_hoer(args) -> int:
    odir = out_dir_for(args.name)
    jpath = odir / f"{args.name}.json"
    if not jpath.is_file():
        print(f"Fehler: kein Ergebnis {args.name} ({jpath} fehlt).", file=sys.stderr)
        return 2
    data = json.loads(jpath.read_text("utf-8"))
    segments = data.get("segments", [])
    if args.stelle is None:
        print((odir / f"{args.name}.hoerliste.txt").read_text("utf-8")
              if (odir / f"{args.name}.hoerliste.txt").is_file() else "Keine Hoerliste.")
        return 0
    flagged = [s for s in segments
               if any(f.startswith(("pruefen:", "heuristik:")) for f in s.get("flags", []))]
    pool = flagged or segments
    idx = max(0, min(args.stelle - 1, len(pool) - 1))
    s = pool[idx]
    start = max(0.0, s["start"] - 7.5)
    end = s["end"] + 7.5
    print(f"Stelle {args.stelle}: {s.get('speaker','?')} {s['start']:.1f}-{s['end']:.1f}s")
    print(f"Text: {s['text']}")
    print(f"Lokal abspielen (~15 s): ffplay -ss {start:.1f} -t {end-start:.1f} "
          f'"{data_root() / "input" / (args.name + ".*")}"')
    print("Hinweis: Beginn/Ende werden begrenzt; funktioniert auch fuer Video-Eingaben "
          "(Tonspur).")
    return 0


def cmd_status(args) -> int:
    info = {"app": APP_VERSION,
            "daten": str(data_root()),
            "modelle": str(data_root() / "modelle"),
            "ohpipe_checkout": os.environ.get("OHPIPE_CHECKOUT", "(nicht eingerichtet)")}
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnose(args) -> int:
    checks = []
    for tool in ("ffmpeg", "ffprobe"):
        pfad = tool_path(tool)
        r = run_cmd([pfad, "-version"])
        checks.append((f"{tool} ({pfad})", r.returncode == 0))
    asr_ok = False
    for profil, cfg in models_config().get("profiles", {}).items():
        d = data_root() / "modelle" / "asr" / cfg.get("asr_model", "")
        if d.is_dir() and any(d.iterdir()):
            asr_ok = True
    checks.append(("modelle-asr (nicht leer)", asr_ok))
    diar_dir = Path(os.environ.get("OHPIPE_DIAR_MODEL",
                                   str(data_root() / "modelle" / "diar")))
    checks.append(("modelle-diar (nicht leer)",
                   diar_dir.is_dir() and any(diar_dir.iterdir())))
    checks.append(("schreibrecht-daten", os.access(data_root(), os.W_OK)
                   if data_root().exists() else True))
    checks.append(("path-eintrag", str(app_root() / "bin") in os.environ.get("PATH", "")))
    try:
        import faster_whisper  # noqa: F401
        checks.append(("faster-whisper", True))
    except ImportError:
        checks.append(("faster-whisper", False))
    ok = all(v for _, v in checks)
    for k, v in checks:
        print(f"{'OK  ' if v else 'FEHLT'}  {k}")
    print("Diagnose enthaelt keine Aufnahmeinhalte oder Zugangsdaten.")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="oh-kette",
                                description="ohpipe-mini Windows-Kern: lokal transkribieren "
                                            "mit Sprechertrennung.")
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kette", help="Eine Datei verarbeiten (Kern inkl. Diarisierung).",
                       description="Medien importieren, lokal transkribieren, Sprecher "
                                   "zuordnen, exportieren. Exitcodes: 0 ok; 2 Eingabe-/"
                                   "Verarbeitungsfehler; 3 Eingabe wird bereits verarbeitet; "
                                   "4 Transkript erhalten, Sprechertrennung fehlgeschlagen.")
    k.add_argument("datei")
    k.add_argument("--sprache", default="de")
    k.add_argument("--sprecher", type=int, default=None)
    k.add_argument("--spur", type=int, default=None)
    k.add_argument("--profil", default="standard", choices=["klein", "standard", "qualitaet"])
    k.add_argument("--nur-transkript", action="store_true")
    k.add_argument("--voll", action="store_true",
                   help="Erweiterung (derzeit Hinweis, blockiert Kern nicht).")
    k.add_argument("--neu", action="store_true")
    k.add_argument("--mock-transkript", default=None,
                   help="Nur Tests/Selbsttest: JSON-Segmente statt Modell.")
    k.set_defaults(func=cmd_kette)
    s = sub.add_parser("stapel", help="Eingabeordner verarbeiten (nicht rekursiv).")
    s.add_argument("ordner", nargs="?")
    s.add_argument("--rekursiv", action="store_true")
    s.add_argument("--sprache", default="de")
    s.add_argument("--sprecher", type=int, default=None)
    s.add_argument("--profil", default="standard")
    s.add_argument("--mock-transkript", default=None)
    s.set_defaults(func=cmd_stapel)
    h = sub.add_parser("hoer", help="Pruefstellen zeigen / Abspielhinweis geben.")
    h.add_argument("name")
    h.add_argument("stelle", nargs="?", type=int, default=None)
    h.set_defaults(func=cmd_hoer)
    for name, fn, help_ in [("status", cmd_status, "Version/Modelle/Verzeichnisse zeigen."),
                            ("diagnose", cmd_diagnose, "Decoder/Modelle/Laufzeit/PATH pruefen.")]:
        q = sub.add_parser(name, help=help_)
        q.set_defaults(func=fn)
    try:
        import ohext
        ohext.register(sub)
    except ImportError as e:
        print(f"Warnung: Erweiterung nicht geladen ({e}).", file=sys.stderr)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
