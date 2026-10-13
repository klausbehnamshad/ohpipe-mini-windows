#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ohpipe-mini Windows-Erweiterung (Neuimplementierung, regelbasiert, ohne LLM).

Abgeleitet von diar2meta 0.1.0 (Regelwerk, offline, Standardbibliothek);
angepasst an die Windows-JSON-Formate (NAME.json statt NAME.diar2.json).
Vorschlaege entstehen durch Regeln aus dem Transkript, nicht durch ein
Sprachmodell, und bleiben von manuell bestaetigten Daten getrennt.
Fixiertes Schema: IMM-Core 1.1.0 (app/schemas/imm-core-1.1.0-core.schema.json).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import ohpipe

IMM_CORE_VERSION = "1.1.0"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "imm-core-1.1.0-core.schema.json"
TODO = "TODO"
CODEBOOK_FORMAT = "ohpipe.l1.codebook.v1"

STOP = set("""
aber alle allem allen aller alles also auch auf aus bei beim bin bis dann damit darum dass dein deine
dem den denen der deren des dich die dies diese diesem diesen dieser dieses doch dort durch eben ein
eine einem einen einer eines einmal etwa etwas euch euer eure fuer gab gibt ganz gar geht gehabt gesagt
gewesen habe haben hast hat hatte hatten heute hier hin hinter ihm ihn ihnen ihr ihre ihrem ihren ihrer
immer ist jetzt jede jedem jeden jeder jedes jemand kann kannst kein keine keinem keinen keiner koennen
machen macht mal man mehr mein meine meinem meinen meiner mich mir mit muss nach nicht nichts noch nun
nur oder ohne schon sehr sein seine seinem seinen seiner seit selbst sich sie sind so soll sollte sondern
sowie ueber um und uns unser unsere unter viel viele vielleicht vom von vor war waren was weil weiter welche
welchem welchen welcher wenn wer werde werden wie wieder will wir wird wissen wo wohl wollen wollte worden
wurde wurden wuerde zum zur zwar zwischen aehm hm mhm genau okay also ja nein naja halt irgendwie the and
that this with from have has had were was what when where which who will would there their they them then
than been being into just like know yeah well really about because could should very some more also only
other over such your youre les des une dans pour avec que qui pas sur est sont mais comme tout tres bien
alors donc
""".split())

ISO3 = {"de": "deu", "en": "eng", "fr": "fra", "lb": "ltz", "auto": "deu"}


def meta_dir(name: str) -> Path:
    return ohpipe.data_root() / "diar2meta" / "output" / name


def load_schema() -> dict:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise RuntimeError(f"IMM-Schema nicht lesbar ({SCHEMA_PATH}): {e}")


def validate(inst, schema, path="$") -> list[str]:
    """Minimale draft-07-Pruefung (Typ, required, enum, const, Muster, allOf)."""
    errs: list[str] = []
    typ = schema.get("type")
    kinds = {"string": str, "array": list, "object": dict, "boolean": bool,
             "number": (int, float), "integer": int}
    if typ and not isinstance(inst, kinds[typ]):
        return [f"{path}: erwartet {typ}"]
    if "const" in schema and inst != schema["const"]:
        errs.append(f"{path}: muss {schema['const']!r} sein")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: {inst!r} nicht zulaessig")
    if isinstance(inst, str):
        if len(inst) < schema.get("minLength", 0):
            errs.append(f"{path}: leer")
        elif "pattern" in schema and not re.fullmatch(schema["pattern"], inst):
            errs.append(f"{path}: passt nicht zu {schema['pattern']}")
        elif schema.get("format") == "date":
            try:
                dt.date.fromisoformat(inst)
            except ValueError:
                errs.append(f"{path}: kein gueltiges Datum")
    if isinstance(inst, list) and "items" in schema:
        for k, item in enumerate(inst):
            errs += validate(item, schema["items"], f"{path}[{k}]")
    if isinstance(inst, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in inst:
                errs.append(f"{path}.{req}: fehlt")
        for key, val in inst.items():
            if key in props:
                errs += validate(val, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}.{key}: Feld gehoert nicht zu IMM-Core")
    for sub in schema.get("allOf", []):
        if "if" in sub:
            if not validate(inst, sub["if"], path):
                errs += validate(inst, sub.get("then", {}), path)
        else:
            errs += validate(inst, sub, path)
    return errs


def todo_paths(obj, path="$") -> list[str]:
    if isinstance(obj, str):
        return [path] if obj.startswith(TODO) else []
    if isinstance(obj, list):
        return [p for k, v in enumerate(obj) for p in todo_paths(v, f"{path}[{k}]")]
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in todo_paths(v, f"{path}.{k}")]
    return []


def load_transcript(name: str) -> tuple[list[dict], dict]:
    odir = ohpipe.out_dir_for(name)
    jpath = odir / f"{name}.json"
    if not jpath.is_file():
        raise FileNotFoundError(f"Kein Kern-Ergebnis fuer {name} ({jpath} fehlt). Erst oh-kette laufen lassen.")
    data = json.loads(jpath.read_text(encoding="utf-8"))
    return data.get("segments", []), data


def keywords(segments: list[dict], n: int = 10) -> list[str]:
    freq: dict[str, int] = {}
    for s in segments:
        for w in re.findall(r"[A-Za-zÄÖÜäöüßÉÉèê]{3,}", s.get("text", "").lower()):
            if w not in STOP:
                freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def chunk_segments(segments: list[dict], target: float = 300.0) -> list[dict]:
    """Teilt lange Interviews in Abschnitte (~target s); mehrstufige Verarbeitung."""
    chunks, cur, start = [], [], None
    for s in segments:
        if start is None:
            start = s["start"]
        cur.append(s)
        if s["end"] - start >= target:
            chunks.append(cur)
            cur, start = [], None
    if cur:
        chunks.append(cur)
    return chunks


def build_draft(name: str) -> tuple[dict, dict, str]:
    segments, data = load_transcript(name)
    lang = ISO3.get(data.get("language", "de"), "deu")
    interviewer = os.environ.get("OHPIPE_INTERVIEWER", "")
    record = {
        "record_id": f"{TODO}: record_id eintragen",
        "interview_date": f"{TODO}: JJJJ-MM-TT eintragen",
        "interviewer": interviewer or f"{TODO}: fragende Person eintragen",
        "consent_status": "",
        "accessRights": "",
        "title": f"{TODO}: beschreibenden Titel eintragen",
        "language": lang,
        "timecoded_segments": [
            {"start": ohpipe.fmt_ts_txt(c[0]["start"]).strip("[]"),
             "end": ohpipe.fmt_ts_txt(c[-1]["end"]).strip("[]"),
             "label": f"{TODO}: Abschnitt {i + 1}"}
            for i, c in enumerate(chunk_segments(segments))],
    }
    words = sum(len(s.get("text", "").split()) for s in segments)
    prov = {
        "tool": f"ohpipe-windows-erweiterung (abgeleitet von diar2meta 0.1.0), {ohpipe.APP_VERSION}",
        "imm_core": IMM_CORE_VERSION,
        "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {"transkript": f"{name}.json", "segmente": len(segments), "woerter": words},
        "status": "entwurf",
        "hinweis": ("consent_status und accessRights werden nie aus dem Gespraech "
                    "abgeleitet, sondern von Hand aus der Einwilligung gesetzt."),
    }
    lines = [f"Pruefliste {name} (IMM-Core {IMM_CORE_VERSION})",
             f"{len(segments)} Segmente, {words} Woerter, Sprache {lang}", "",
             "VON HAND AUSFUELLEN:",
             "- consent_status (Einwilligung; nie aus dem Gespraech erfunden)",
             "- accessRights (open | restricted | closed)",
             "- record_id, interview_date, interviewer, title", "",
             "BESTAETIGEN:",
             "- timecoded_segments: TODO-Labels sachlich beschreiben",
             "- Segmentvorschlaege (entwurf) bleiben getrennt, bis sie uebernommen werden."]
    return record, prov, "\n".join(lines) + "\n"


PII_PATTERNS = [
    ("anrede-name", re.compile(r"\b(Herr|Frau)\s+[A-ZÄÖÜ][a-zäöüß]+")),
    ("e-mail", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("telefon", re.compile(r"(\+?\d[\d\s/()-]{7,}\d)")),
    ("adresse", re.compile(r"\b[A-ZÄÖÜ][a-zäöüß]+(straße|strasse|gasse|weg|allee)\s+\d+", re.IGNORECASE)),
    ("plz-ort", re.compile(r"\b[ALDFB]\s?\d{4,5}\s+[A-ZÄÖÜ][a-zäöüß]+")),
]


def pii_check(name: str) -> list[dict]:
    segments, _ = load_transcript(name)
    hits = []
    for s in segments:
        for kind, rx in PII_PATTERNS:
            for m in rx.finditer(s.get("text", "")):
                hits.append({"segment": s["id"], "start": s["start"], "art": kind,
                             "fund": m.group(0)[:60]})
    if re.search(r"[A-ZÄÖÜ][a-zäöüß]+", name):
        hits.append({"segment": "-", "start": 0.0, "art": "dateiname",
                     "fund": "Dateiname enthaelt moeglicherweise einen Namen — pruefen"})
    return hits


def build_vorschlaege(name: str) -> dict:
    """Lokale Vorschlaege (Regeln, kein Sprachmodell): 3 Titel, Abstract, Keywords, Labels."""
    segments, data = load_transcript(name)
    kws = keywords(segments)
    speakers = sorted({s.get("speaker", "?") for s in segments})
    dauer = max((s["end"] for s in segments), default=0.0)
    titel = [
        f"Interview ({len(speakers)} Stimmen, {dauer / 60:.0f} Minuten): {', '.join(kws[:3]) or 'Gespraech'}",
        f"Gespraech ueber {', '.join(kws[:2]) or 'Alltag und Erinnerung'}",
        f"{name}: {', '.join(kws[2:5]) or 'Erzählung und Nachfragen'}",
    ]
    top = sorted(segments, key=lambda s: len(s.get("text", "")), reverse=True)[:3]
    abstract = ("Das Gespraech dauert %.1f Minuten mit %d Stimmen (%s). " % (
        dauer / 60, len(speakers), ", ".join(speakers)))
    if top:
        abstract += "Breit ausgefuehrt wird unter anderem: „%s“. " % top[0]["text"][:120]
    abstract += "Schwerpunkte: %s." % (", ".join(kws[:5]) or "Alltag")
    labels = []
    for i, c in enumerate(chunk_segments(segments)):
        ck = keywords(c, 3)
        labels.append({"abschnitt": i + 1,
                       "start": c[0]["start"], "end": c[-1]["end"],
                       "name": f"Abschnitt {i + 1}: {', '.join(ck) or 'Gespraechsverlauf'}"})
    return {"titel_optionen": titel, "abstract": abstract,
            "schlagwoerter": kws[:10], "segmentnamen": labels,
            "methode": "regelbasiert-ohne-sprachmodell",
            "hinweis": "Beschreibend, ohne beabsichtigte Personennamen."}


QUESTION_WORDS = {"wer", "was", "wann", "wo", "warum", "wieso", "wie", "welche",
                  "erzaehlen", "what", "when", "where", "why", "how", "où", "comment",
                  "pourquoi", "quand"}


def is_question(text: str) -> bool:
    t = text.strip().lower()
    return t.endswith("?") or (len(t.split()) >= 4 and t.split()[0].rstrip(",") in QUESTION_WORDS)


def build_l1(name: str, codebuch: str | None = None, nur_fragen: bool = False) -> dict:
    """L1-Neuimplementierung: Fragenleitfaden + Rohcodes mit woertlichen Belegen."""
    segments, data = load_transcript(name)
    speakers = sorted({s.get("speaker", "?") for s in segments})
    fragen = [{"zeit": s["start"], "sprecher": s.get("speaker", "?"), "text": s["text"]}
              for s in segments if is_question(s.get("text", ""))]
    if nur_fragen:
        return {"fragenleitfaden": fragen, "rollen_status": data.get("role_status", "unbestaetigt"),
                "hinweis": "Ohne Sprachmodell; unbestätigte Rollen sichtbar."}
    allowed = None
    if codebuch:
        allowed = [ln.split("=")[0].strip() for ln in Path(codebuch).read_text("utf-8").splitlines()
                   if "=" in ln and not ln.strip().startswith(("#", "["))]
    codes = []
    for s in segments:
        words = s.get("text", "").split()
        if len(words) < 4:
            codes.append({"segment": s["id"], "code": "KURZ", "beleg": s["text"],
                          "verankert": True})
            continue
        kws = keywords([s], 2)
        code = (allowed[0] if allowed else ("_".join(kws) or "thema").upper()[:40])
        beleg = s["text"][:140]
        codes.append({"segment": s["id"], "sprecher": s.get("speaker", "?"),
                      "code": code, "beleg": beleg,
                      "verankert": beleg.split()[0] in s["text"] if beleg else False})
    cats: dict[str, list] = {}
    for c in codes:
        cats.setdefault(c["code"], []).append(c["segment"])
    # Auf 8–15 Kategorien bringen: kleine zusammenfassen, große behalten.
    while len(cats) > 15:
        kleinste = sorted(cats, key=lambda k: len(cats[k]))[:2]
        a, b = kleinste[0], kleinste[1]
        cats[f"{a}+{b}"] = cats.pop(a) + cats.pop(b)
    verankert = sum(1 for c in codes if c["verankert"])
    return {"fragenleitfaden": fragen, "rohcodes": codes, "kategorien": sorted(cats),
            "codebuch_format": CODEBOOK_FORMAT, "codebuch": codebuch or "vorschlag",
            "statistik": {"segmente": len(codes), "verankert": verankert,
                          "anteil_verankert": round(verankert / max(len(codes), 1), 3)}}


def mark_stale(name: str) -> None:
    mdir = meta_dir(name)
    if mdir.is_dir():
        (mdir / "VERALTET.txt").write_text(
            "Abhaengige Vorschlaege sind nach Rollen-/Textaenderung veraltet. "
            "Bitte entwurf/l1 pruefen und ggf. neu erstellen.\n", encoding="utf-8")


def voll_chain(name: str) -> int:
    """Transkript -> IMM-Entwurf -> Vorschlaege -> PII-Pruefung -> Pruefliste."""
    mdir = meta_dir(name)
    mdir.mkdir(parents=True, exist_ok=True)
    record, prov, pruef = build_draft(name)
    ohpipe.atomic_write(mdir / f"{name}.imm.draft.json",
                        json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    ohpipe.atomic_write(mdir / f"{name}.imm.provenance.json",
                        json.dumps(prov, ensure_ascii=False, indent=2) + "\n")
    ohpipe.atomic_write(mdir / f"{name}.entwurf.json",
                        json.dumps(build_vorschlaege(name), ensure_ascii=False, indent=2) + "\n")
    hits = pii_check(name)
    ohpipe.atomic_write(mdir / f"{name}.pii.json",
                        json.dumps(hits, ensure_ascii=False, indent=2) + "\n")
    extra = f"\nPII-Hinweise: {len(hits)} Treffer (keine garantierte Anonymisierung)."
    ohpipe.atomic_write(mdir / f"{name}.pruefliste.txt", pruef + extra + "\n")
    print(f"Vollkette {name}: Entwurf + Vorschlaege + PII ({len(hits)}) + Pruefliste in {mdir}")
    return 0


def cmd_entwurf(args) -> int:
    mdir = meta_dir(args.name)
    mdir.mkdir(parents=True, exist_ok=True)
    zpath = mdir / f"{args.name}.entwurf.json"
    if zpath.is_file() and not args.neu and not args.nur:
        print(f"Entwurfsvorschlaege bestehen ({zpath}). Mit --neu ersetzen.")
        return 0
    v = build_vorschlaege(args.name)
    if args.nur:
        if args.nur not in ("titel", "abstract", "keywords", "labels"):
            print("Fehler: --nur kennt titel|abstract|keywords|labels.", flush=True)
            return 2
        alt = json.loads(zpath.read_text("utf-8")) if zpath.is_file() else {}
        key = {"titel": "titel_optionen", "abstract": "abstract",
               "keywords": "schlagwoerter", "labels": "segmentnamen"}[args.nur]
        alt[key] = v[key]
        v = alt
    ohpipe.atomic_write(zpath, json.dumps(v, ensure_ascii=False, indent=2) + "\n")
    print(f"Vorschlaege geschrieben: {zpath}")
    return 0


def cmd_pruefen(args) -> int:
    hits = pii_check(args.name)
    if not hits:
        print("Keine personenbezogenen Hinweise gefunden (keine Garantie).")
        return 0
    for h in hits:
        print(f'{h["start"]:7.1f}s [{h["segment"]}] {h["art"]}: {h["fund"]}')
    print(f"\n{len(hits)} Treffer. Namenspruefung ist keine garantierte Anonymisierung.")
    return 0


def cmd_uebernehmen(args) -> int:
    mdir = meta_dir(args.name)
    draft_p = mdir / f"{args.name}.imm.draft.json"
    vor_p = mdir / f"{args.name}.entwurf.json"
    if not draft_p.is_file() or not vor_p.is_file():
        print("Fehler: Entwurf oder Vorschlaege fehlen.", flush=True)
        return 2
    draft = json.loads(draft_p.read_text("utf-8"))
    vor = json.loads(vor_p.read_text("utf-8"))
    (mdir / f"{args.name}.imm.draft.bak.json").write_bytes(draft_p.read_bytes())
    for field in args.felder:
        if field == "titel":
            nr = (args.titel_nr or 1) - 1
            draft["title"] = vor["titel_optionen"][nr]
        elif field == "abstract":
            draft["abstract"] = vor["abstract"]
        elif field == "keywords":
            draft["keywords"] = vor["schlagwoerter"]
        elif field == "labels":
            segs = draft.get("timecoded_segments", [])
            for i, lab in enumerate(vor["segmentnamen"]):
                if i < len(segs):
                    segs[i]["label"] = lab["name"]
        else:
            print(f"Fehler: unbekanntes Feld {field!r} (titel|abstract|keywords|labels).", flush=True)
            return 2
    schema = load_schema()
    errs = [e for e in validate(draft, schema) if ".consent_status" not in e and ".accessRights" not in e]
    ohpipe.atomic_write(draft_p, json.dumps(draft, ensure_ascii=False, indent=2) + "\n")
    print(f"Uebernommen ({', '.join(args.felder)}), Sicherung .bak.json. "
          f"Offene Schemafelder: {len(errs)} (u. a. Rechte bleiben Handarbeit).")
    return 0


ROLLEN = ("fragend", "interviewt", "dritte")


def parse_rollen(paare, bekannte: set) -> tuple:
    """Parst ROLLE=SPK_xx-Paare. Gibt (rollen, fehlermeldung) zurueck."""
    rollen: dict = {}
    for paar in paare or []:
        rolle, trenn, spk = (paar or "").partition("=")
        rolle, spk = rolle.strip(), spk.strip()
        if not trenn or not rolle or not spk:
            return None, (f"ungueltig {paar!r} (Form ROLLE=SPK_xx, "
                           f"z. B. fragend=SPK_01)")
        if rolle not in ROLLEN:
            return None, (f"unbekannte Rolle {rolle!r} "
                           f"(moeglich: {', '.join(ROLLEN)})")
        if rolle in rollen:
            return None, (f"doppelte Rolle {rolle!r} "
                           f"(bereits {rollen[rolle]} zugeordnet)")
        if spk in rollen.values():
            return None, f"{spk} ist bereits einer Rolle zugeordnet"
        if spk not in bekannte:
            return None, (f"unbekannter Sprecher {spk!r} "
                           f"(vorhanden: {', '.join(sorted(bekannte)) or 'keine'})")
        rollen[rolle] = spk
    return rollen, None


def erste_stimme(data: dict) -> str | None:
    """Zuerst sprechende Stimme nach Segmentreihenfolge (fuer --tausch)."""
    for s in data.get("segments", []):
        if s.get("speaker") not in (None, "SPK_??", "?"):
            return s["speaker"]
    return None


def cmd_rollen(args) -> int:
    """Nur Rollen aendern — stabile Sprecherkennungen (Segmente, Woerter,
    Turns, Exporte) bleiben grundsaetzlich unangetastet."""
    odir = ohpipe.out_dir_for(args.name)
    jpath = odir / f"{args.name}.json"
    if not jpath.is_file():
        print(f"Fehler: kein Ergebnis {args.name} ({jpath} fehlt). "
              f"Erst oh-kette laufen lassen.", file=sys.stderr)
        return 2
    try:
        data = json.loads(jpath.read_text("utf-8"))
    except ValueError as e:
        print(f"Fehler: Ergebnisdatei unlesbar ({e}).", file=sys.stderr)
        return 2
    speakers = sorted({s.get("speaker") for s in data.get("segments", [])})
    if args.tausch:
        if len(speakers) != 2 or "SPK_??" in speakers:
            print("Fehler: --tausch nur bei genau zwei zugeordneten Sprechern; "
                  "sonst --setzt ROLLE=SPK_xx ... angeben.", file=sys.stderr)
            return 2
        alt = data.get("roles") or {}
        if "fragend" in alt and "interviewt" in alt:
            data["roles"] = {"fragend": alt["interviewt"],
                             "interviewt": alt["fragend"]}
        else:
            erste = erste_stimme(data) or speakers[0]
            zweite = next(sp for sp in speakers if sp != erste)
            data["roles"] = {"fragend": zweite, "interviewt": erste}
    elif args.setzt:
        bekannte = {sp for sp in speakers if sp not in (None, "SPK_??", "?")}
        rollen, fehler = parse_rollen(args.setzt, bekannte)
        if fehler is not None:
            print(f"Fehler: {fehler}.", file=sys.stderr)
            return 2
        data["roles"] = rollen
    else:
        print("Fehler: --tausch oder --setzt ROLLE=SPK_xx ... angeben "
              "(z. B. --setzt fragend=SPK_01 interviewt=SPK_02).",
              file=sys.stderr)
        return 2
    data["role_status"] = "bestaetigt-hand"
    bak = jpath.with_suffix(jpath.suffix + ".bak")
    try:
        bak.write_bytes(jpath.read_bytes())
    except OSError:
        pass
    ohpipe.atomic_write(jpath, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    mark_stale(args.name)
    print(f"Rollen aktualisiert ({data['roles']}); Sprecherkennungen unveraendert, "
          f"abhaengige Vorschlaege als veraltet markiert.")
    return 0


def cmd_l1(args) -> int:
    mdir = meta_dir(args.name)
    mdir.mkdir(parents=True, exist_ok=True)
    res = build_l1(args.name, codebuch=args.codebuch, nur_fragen=args.nur_fragen)
    ohpipe.atomic_write(mdir / f"{args.name}.l1.entwurf.json",
                        json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    if not args.nur_fragen:
        lines = [f"# Codebuch-Vorschlag ({CODEBOOK_FORMAT}) — menschliche Pruefung noetig", ""]
        for c in res["kategorien"]:
            lines += [f"[{c}]", 'definition = "TODO: offene Definition von Hand schliessen"', ""]
        ohpipe.atomic_write(mdir / f"{args.name}.codebuch.vorschlag.toml",
                            "\n".join(lines))
        st = res["statistik"]
        print(f"L1: {st['segmente']} Segmente, {st['verankert']} verankert "
              f"({st['anteil_verankert']:.0%}), {len(res['kategorien'])} Kategorien.")
    else:
        print(f"Fragenleitfaden: {len(res['fragenleitfaden'])} Fragen (ohne Sprachmodell).")
    return 0


def cmd_bericht(args) -> int:
    root = ohpipe.data_root() / "diar2" / "output"
    zeilen = ["# Bericht", ""]
    for odir in sorted(root.iterdir()) if root.is_dir() else []:
        for j in odir.glob("*.run.json"):
            run = json.loads(j.read_text("utf-8"))
            zeilen.append(f"- {run.get('name')}: {run.get('status')} "
                          f"({run.get('dauer_s', '?')} s, {run.get('app', '?')})")
    text = "\n".join(zeilen) + "\n"
    if args.ausgabe:
        Path(args.ausgabe).write_text(text, encoding="utf-8")
        print(f"Bericht nach {args.ausgabe} geschrieben.")
    else:
        print(text)
    return 0


def cmd_imm_todo(args) -> int:
    root = ohpipe.data_root() / "diar2meta" / "output"
    n = 0
    for mdir in sorted(root.iterdir()) if root.is_dir() else []:
        for d in mdir.glob("*.imm.draft.json"):
            rec = json.loads(d.read_text("utf-8"))
            offene = todo_paths(rec)
            print(f"{mdir.name}: {len(offene)} offene Felder")
            n += 1
    if not n:
        print("Keine Entwuerfe.")
    return 0


def cmd_imm_check(args) -> int:
    schema = load_schema()
    ok = True
    for p in args.dateien:
        try:
            rec = json.loads(Path(p).read_text("utf-8"))
        except (OSError, ValueError) as e:
            print(f"FEHLER {p}: {e}")
            ok = False
            continue
        errs, todos = validate(rec, schema), todo_paths(rec)
        if errs or todos:
            print(f"OFFEN {p}: {len(errs)} Schema-, {len(todos)} TODO-Eintraege")
            ok = False
        else:
            print(f"GEPRUEFT {p}: IMM-Core {IMM_CORE_VERSION}")
    return 0 if ok else 1


def cmd_imm_schema_sync(args) -> int:
    import urllib.request
    url = "https://doi.org/10.5281/zenodo.20507329"
    print(f"Ausdruecklicher Online-Abgleich: {url}")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            print(f"DOI aufloesbar (HTTP {r.status}). Lokale Dateien werden NICHT geaendert.")
    except Exception as e:  # noqa: BLE001 — Diagnoseausgabe ist hier gewollt
        print(f"Abgleich fehlgeschlagen (offline ok): {e}")
        return 1
    print(f"Lokal fixiert: IMM-Core {IMM_CORE_VERSION} ($id zenodo.20507329).")
    return 0


def register(sub) -> None:
    e = sub.add_parser("entwurf", help="Titel/Abstract/Keywords/Labels lokal vorschlagen.")
    e.add_argument("name")
    e.add_argument("--neu", action="store_true")
    e.add_argument("--nur", default=None)
    e.set_defaults(func=cmd_entwurf)
    p = sub.add_parser("pruefen", help="Entwurf auf personenbezogene Hinweise pruefen.")
    p.add_argument("name")
    p.set_defaults(func=cmd_pruefen)
    u = sub.add_parser("uebernehmen", help="Vorschlaege nach Sicherung uebernehmen.")
    u.add_argument("name")
    u.add_argument("felder", nargs="+")
    u.add_argument("--titel-nr", type=int, default=1)
    u.set_defaults(func=cmd_uebernehmen)
    r = sub.add_parser(
        "rollen", help="Rollen tauschen/setzen (keine Modelle).",
        description="Aendert nur Rollen (fragend/interviewt/dritte); stabile "
                    "Sprecherkennungen, Woerter, Turns und Exporte bleiben "
                    "unveraendert. --tausch: bestaetigte Vertauschung bei genau "
                    "zwei Stimmen (bestehende Rollen tauschen, sonst erste Stimme "
                    "= interviewt). --setzt: explizit, Form ROLLE=SPK_xx, "
                    "z. B. --setzt fragend=SPK_01 interviewt=SPK_02.")
    r.add_argument("name")
    r.add_argument("--tausch", action="store_true")
    r.add_argument("--setzt", nargs="*", default=None)
    r.set_defaults(func=cmd_rollen)
    l = sub.add_parser("l1", help="Fragenleitfaden und L1-Codierung (regelbasiert).")
    l.add_argument("name")
    l.add_argument("--nur-fragen", action="store_true")
    l.add_argument("--codebuch", default=None)
    l.add_argument("--neu", action="store_true")
    l.set_defaults(func=cmd_l1)
    b = sub.add_parser("bericht", help="Uebersicht ueber Interviews.")
    b.add_argument("--ausgabe", default=None)
    b.set_defaults(func=cmd_bericht)
    t = sub.add_parser("imm-todo", help="Offene Felder je Interview.")
    t.set_defaults(func=cmd_imm_todo)
    c = sub.add_parser("imm-check", help="Entwurf offline gegen IMM-Core 1.1.0 pruefen.")
    c.add_argument("dateien", nargs="+")
    c.set_defaults(func=cmd_imm_check)
    s = sub.add_parser("imm-schema-sync", help="Schema nur auf Aufruf online vergleichen.")
    s.set_defaults(func=cmd_imm_schema_sync)
