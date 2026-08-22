#!/usr/bin/env python3
"""kaikki + Lexique + edits -> build/lexicon.jsonl, la forme canonique.

Deux shells lisent ce fichier et rien d'autre : le XML d'Apple et la seed Mongo.
Tout ce qui est une décision de contenu se prend ici, une seule fois, pour les
deux — sinon la fenêtre de Dictionary.app et le site finissent par ne plus dire
la même chose, et personne ne s'en aperçoit avant six mois.

Ce que le script décide :

  1. **Une entrée par vedette, pas par partie du discours.** kaikki donne
     « aller » deux fois — verbe et nom. On cherche un mot, pas une catégorie :
     les deux tiennent sur la même page, en sections. C'est aussi ce qui rend
     l'index des formes trivial, puisqu'une forme mène à un mot et non à un
     couple mot×catégorie.

  2. **La morphologie vient de Lexique, pas de kaikki.** Mesuré : 600 formes
     fléchies dans tout le dump kaikki, contre 125 653 dans Lexique. Chercher
     « allions » dans un dictionnaire qui ne connaît que « aller » ne donne
     rien, et « allions » est exactement ce qu'on tape quand on lit.

  3. **La coupe se fait par fréquence de lemme**, pas par ordre alphabétique ni
     par longueur du dump. `--top 3000` sort les trois mille lemmes français les
     plus fréquents qui ont une glose. Le reste attend.

Usage :  python3 scripts/normalize.py [--top N] [--all] [--stats]
"""

import collections
import csv
import json
import re
import sys
import unicodedata

import sources as S

# --- l'analyse d'une forme fléchie ------------------------------------------

# Lexique code le verbe en mode:temps:personne. On le rend lisible. Les noms de
# temps restent en français : ce sont les noms propres de catégories françaises,
# c'est sous ces noms qu'ils sont appris, et ce bundle est fait pour vivre à
# côté de Conjugaison, qui les écrit ainsi.
MODES = {
    "ind": "indicatif", "sub": "subjonctif", "cnd": "conditionnel",
    "imp": "impératif", "inf": "infinitif", "par": "participe",
}
TEMPS = {
    "pre": "présent", "imp": "imparfait", "pas": "passé simple", "fut": "futur",
}
PERSONNES = {
    "1s": "ngôi 1 số ít", "2s": "ngôi 2 số ít", "3s": "ngôi 3 số ít",
    "1p": "ngôi 1 số nhiều", "2p": "ngôi 2 số nhiều", "3p": "ngôi 3 số nhiều",
}
GENRE = {"m": "giống đực", "f": "giống cái"}
NOMBRE = {"s": "số ít", "p": "số nhiều"}


def de(mot):
    """« de » devant un mot : élision sur voyelle, sinon « du ».

    Sans ça on écrit « présent du impératif », qui n'est pas du français et qui
    est la première chose qu'un lecteur francophone verra sur la page.
    """
    return f"de l'{mot}" if mot[0] in "aeiouâêîôûéèh" else f"du {mot}"


def analyse_verbe(code):
    """« ind:imp:1p » -> « imparfait de l'indicatif · ngôi 1 số nhiều »."""
    parts = code.split(":")
    if not parts:
        return None
    mode = MODES.get(parts[0])
    if mode is None:
        return None
    if parts[0] == "inf":
        return "infinitif"
    # « par:pas » est le participe *passé*, pas le passé simple. Le même code
    # « pas » veut dire deux choses selon le mode, et les confondre donnait
    # « bu : participe passé simple » — une case qui n'existe pas.
    if parts[0] == "par":
        temps = {"pas": "passé", "pre": "présent"}.get(parts[1]) if len(parts) > 1 else None
        return f"participe {temps}" if temps else "participe"
    temps = TEMPS.get(parts[1]) if len(parts) > 1 else None
    label = f"{temps} {de(mode)}" if temps else mode
    personne = PERSONNES.get(parts[2]) if len(parts) > 2 else None
    return f"{label} · {personne}" if personne else label


def analyse(row):
    """La ligne Lexique -> les analyses de cette forme, une par élément.

    Une liste et non une phrase, parce que Lexique répartit les analyses d'une
    même forme sur plusieurs lignes homographes : « sois » sort une fois comme
    subjonctif présent, une autre fois comme impératif *et* subjonctif. Joindre
    trop tôt donnait deux lignes dont l'une répétait l'autre. On rend les
    éléments, l'index les fusionne, et la page n'affiche chaque analyse qu'une
    fois.

    Elles sont toutes gardées : « allons » est impératif *et* indicatif présent,
    et choisir serait mentir sur une ambiguïté que le français a vraiment.
    """
    if row["infover"]:
        codes = [c for c in row["infover"].split(";") if c]
        labels = [analyse_verbe(c) for c in codes]
        return [l for l in dict.fromkeys(labels) if l]
    bits = [GENRE.get(row["genre"]), NOMBRE.get(row["nombre"])]
    joined = " ".join(b for b in bits if b)
    return [joined] if joined else []


# --- lecture des sources ----------------------------------------------------

def load_lexique():
    """ortho -> [(lemme, analyse)], et lemme -> fréquence.

    La fréquence est la moyenne films+livres par million, telle que conjugaison
    la calcule déjà. Deux corpus valent mieux qu'un : les sous-titres sur-notent
    la parole, les livres l'écrit, et ce dictionnaire sert les deux.
    """
    forms = collections.defaultdict(list)
    freq = {}
    with open(S.LEXIQUE, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            ortho, lemme = row["ortho"].strip(), row["lemme"].strip()
            if not ortho or not lemme:
                continue
            try:
                f2 = float(row["freqlemfilms2"] or 0)
                fl = float(row["freqlemlivres"] or 0)
            except ValueError:
                f2 = fl = 0.0
            freq[lemme] = max(freq.get(lemme, 0.0), (f2 + fl) / 2)
            if ortho != lemme:
                forms[ortho].append((lemme, analyse(row)))
    return forms, freq


def clean(text):
    """Le Wiktionnaire laisse passer des espaces insécables et des retours."""
    return re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip()


def load_kaikki():
    """Les lignes kaikki regroupées par vedette."""
    by_word = collections.defaultdict(list)
    for line in open(S.KAIKKI_FR, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("word"):
            by_word[row["word"]].append(row)
    return by_word


# --- construction d'une entrée ----------------------------------------------

def build_senses(row):
    out = []
    for sense in row.get("senses", []):
        glosses = [clean(g) for g in sense.get("glosses", []) if clean(g)]
        if not glosses:
            continue
        tags = [t for t in sense.get("tags", []) if t != "no-gloss"]
        examples = []
        for ex in sense.get("examples", []):
            src = clean(ex.get("text"))
            if not src:
                continue
            examples.append({"fr": src, "vi": clean(ex.get("translation")) or None})
        out.append({
            "gloss": glosses[0],
            "sub": glosses[1:],
            "tags": tags,
            "examples": examples,
        })
    return out


def words_of(items):
    """[{'word': x}] -> [x], sans doublon et dans l'ordre."""
    seen = {}
    for it in items or []:
        w = clean(it.get("word") if isinstance(it, dict) else it)
        if w:
            seen[w] = None
    return list(seen)


def build_entry(headword, rows, freq):
    """Les lignes kaikki d'une même vedette -> une entrée, sections par catégorie."""
    blocks, ipa, audio = [], [], None
    derived, related, syn, ant = [], [], [], []

    for row in rows:
        senses = build_senses(row)
        if not senses:
            continue
        blocks.append({
            "pos": row.get("pos") or "",
            # pos_title est le vietnamien du Wiktionnaire, et il est plus fin
            # que pos : « Ngoại động từ » / « Nội động từ » là où pos dit « verb ».
            # C'est une information sur le français, écrite pour un lecteur
            # vietnamien. On la garde telle quelle.
            "pos_vi": clean(row.get("pos_title")) or None,
            "tags": row.get("tags", []),
            "senses": senses,
        })
        for sound in row.get("sounds", []):
            if sound.get("ipa") and sound["ipa"].startswith("/"):
                ipa.append(sound["ipa"])
            if audio is None and sound.get("mp3_url"):
                audio = sound["mp3_url"]
        derived += words_of(row.get("derived"))
        related += words_of(row.get("related"))
        syn += words_of(row.get("synonyms"))
        ant += words_of(row.get("antonyms"))

    if not blocks:
        return None

    return {
        "id": f"fr:{headword}",
        "lang": "fr",
        "headword": headword,
        "rank": freq.get(headword, 0.0),
        "ipa": list(dict.fromkeys(ipa))[:3],
        "audio": audio,
        "blocks": blocks,
        "derived": list(dict.fromkeys(derived)),
        "related": list(dict.fromkeys(related)),
        "synonyms": list(dict.fromkeys(syn)),
        "antonyms": list(dict.fromkeys(ant)),
    }


# --- les retouches ----------------------------------------------------------

def apply_edits(entries):
    """base ⊕ edits. Le fichier est en git, la base n'y est pas.

    Une retouche est un patch de fusion par id : les clés présentes remplacent,
    les absentes laissent en place. Une retouche sans entrée de base crée une
    entrée — c'est comme ça que « faire », que le Wiktionnaire vietnamien n'a
    pas, entrera dans le dictionnaire.
    """
    path = S.ROOT / "data" / "edits.jsonl"
    if not path.exists():
        return 0
    n = 0
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        patch = json.loads(line)
        eid = patch.get("id")
        if not eid:
            continue
        base = entries.get(eid)
        if base is None:
            patch.setdefault("lang", "fr")
            patch.setdefault("headword", eid.split(":", 1)[1])
            patch.setdefault("blocks", [])
            patch.setdefault("rank", 0.0)
            entries[eid] = patch
        else:
            base.update({k: v for k, v in patch.items() if k != "id"})
        entries[eid]["edited"] = True
        n += 1
    return n


# --- sortie -----------------------------------------------------------------

def main():
    argv = sys.argv[1:]
    top = 3000
    if "--top" in argv:
        top = int(argv[argv.index("--top") + 1])
    if "--all" in argv:
        top = None

    print("  lecture de Lexique…")
    forms, freq = load_lexique()
    print(f"    {len(forms)} formes fléchies, {len(freq)} lemmes")

    print("  lecture de kaikki…")
    by_word = load_kaikki()
    print(f"    {len(by_word)} vedettes")

    # La coupe. On classe les vedettes par fréquence du lemme et on garde les N
    # premières — une vedette absente de Lexique a une fréquence de zéro et passe
    # donc en queue, ce qui est le bon comportement : ce sont les mots rares.
    ranked = sorted(by_word, key=lambda w: (-freq.get(w, 0.0), w))
    kept = ranked if top is None else ranked[:top]

    entries = {}
    for headword in kept:
        entry = build_entry(headword, by_word[headword], freq)
        if entry:
            entries[entry["id"]] = entry

    n_edits = apply_edits(entries)

    # L'index des formes, restreint à ce qu'on a gardé. Une forme dont le lemme
    # n'est pas dans la coupe ne sert à rien : elle mènerait à une page absente.
    heads = {e["headword"] for e in entries.values()}
    index = collections.defaultdict(list)
    for form, targets in forms.items():
        merged = {}
        for lemme, labels in targets:
            if lemme not in heads:
                continue
            # dict.fromkeys plutôt qu'un set : l'ordre des analyses est celui de
            # Lexique, qui va du plus courant au moins, et c'est l'ordre qu'on veut lire.
            merged.setdefault(lemme, {}).update(dict.fromkeys(labels))
        for lemme, labels in merged.items():
            index[form].append({"lemma": lemme,
                                "analysis": ", ".join(labels) or None})

    S.BUILD.mkdir(exist_ok=True)
    out = S.BUILD / "lexicon.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for entry in sorted(entries.values(), key=lambda e: -e["rank"]):
            entry["forms"] = sorted(
                (form for form, t in index.items()
                 if any(x["lemma"] == entry["headword"] for x in t)),
                key=str.lower)
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    idx = S.BUILD / "forms.json"
    idx.write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")

    n_senses = sum(len(b["senses"]) for e in entries.values() for b in e["blocks"])
    n_ex = sum(len(s["examples"]) for e in entries.values()
               for b in e["blocks"] for s in b["senses"])
    print(f"\n  {len(entries)} entrées, {n_senses} sens, {n_ex} exemples, "
          f"{len(index)} formes fléchies indexées")
    if n_edits:
        print(f"  {n_edits} retouches appliquées")
    print(f"  → {out.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
