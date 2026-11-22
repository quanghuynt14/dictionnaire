#!/usr/bin/env python3
"""entries.md -> data/reindoo-vi.jsonl, les entrées Việt–Pháp de reindoo.

Mille mots vietnamiens, les plus fréquents, écrits pour un francophone :
des équivalents français, un sens par différence à apprendre, des étiquettes,
des exemples, une note sur l'erreur qu'un francophone fait. Ils viennent de
l'étude dict-study (brouillon de Claude Opus sur preuves — Wiktionnaires et
vraies phrases —, puis relecture par un second Opus).

Ce n'est pas du Wiktionnaire, et ils ne le remplacent pas : emit_mongo les
place **avant** les sens du Wiktionnaire, qui restent tels quels.

Le format d'entrée, un bloc par mot :

    # trắng
    1. (Adjectif) blanc
       [familier]
       ex: Cà vạt đen hay trắng? = Cravate noire ou blanche ?
       note: …

Le script refuse une ligne qu'il ne comprend pas plutôt que de la perdre.

Usage :  python3 scripts/import_reindoo.py CHEMIN/entries.md
"""

import json
import re
import sys
import unicodedata

import sources as S

SENSE = re.compile(r"(\d+)\.\s*\(([^)]*)\)\s*(.+)")
LABELS = re.compile(r"(\[[^\]]+\]\s*)+")
EXAMPLE = re.compile(r"ex:\s*(.+?)\s+=\s+(.+)")


def nfc(s):
    return unicodedata.normalize("NFC", s.strip())


def parse(block):
    lines = [l for l in block.strip().splitlines() if l.strip()]
    head = re.fullmatch(r"#\s*(.+)", lines[0].strip())
    if not head:
        raise ValueError(f"pas de vedette : {lines[0]!r}")
    word = nfc(head.group(1))
    senses = []
    for raw in lines[1:]:
        line = raw.strip()
        if m := SENSE.fullmatch(line):
            senses.append({"pos": m.group(2).strip(), "labels": [], "gloss": nfc(m.group(3)),
                           "examples": [], "note": ""})
            continue
        if not senses:
            raise ValueError(f"{word} : ligne avant le premier sens : {line!r}")
        sense = senses[-1]
        if LABELS.fullmatch(line):
            sense["labels"] += [l.strip() for l in re.findall(r"\[([^\]]+)\]", line)]
        elif m := EXAMPLE.fullmatch(line):
            sense["examples"].append({"src": nfc(m.group(1)), "tr": nfc(m.group(2))})
        elif line.startswith("note:"):
            note = nfc(line[5:])
            sense["note"] = f"{sense['note']} {note}".strip()
        else:
            raise ValueError(f"{word} : ligne inconnue : {line!r}")
    if not senses:
        raise ValueError(f"{word} : aucun sens")
    return {"word": word, "senses": senses}


def main():
    src = sys.argv[1]
    text = open(src, encoding="utf-8").read()
    entries = [parse(b) for b in re.findall(r"```[a-z]*\n(.*?)```", text, re.S)]
    words = [e["word"] for e in entries]
    if len(set(words)) != len(words):
        raise SystemExit("vedette en double")
    out = S.ROOT / "data" / "reindoo-vi.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    n_senses = sum(len(e["senses"]) for e in entries)
    print(f"  {len(entries):,} entrées, {n_senses:,} sens → {out.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
