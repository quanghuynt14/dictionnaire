#!/usr/bin/env python3
"""kaikki + morphologie + retouches -> build/lexicon-LL.jsonl, la forme canonique.

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

  2. **La morphologie ne vient jamais de kaikki.** Mesuré : 600 formes fléchies
     dans le dump français, 8 014 dans l'anglais pour 119 166 vedettes. Chaque
     langue a son module — `morph_fr`, `morph_en` — et c'est le seul endroit où
     les deux dictionnaires diffèrent vraiment.

  3. **La coupe se fait par fréquence de lemme.** `--top 3000` sort les trois
     mille lemmes les plus fréquents qui ont une glose. Le reste attend.

Usage :  python3 scripts/normalize.py --lang fr [--top N] [--all]
"""

import collections
import importlib
import json
import re
import sys
import urllib.parse

import sources as S


def clean(text):
    """Le Wiktionnaire laisse passer des espaces insécables et des retours."""
    return re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip()


def load_kaikki(path):
    """Les lignes kaikki regroupées par vedette."""
    by_word = collections.defaultdict(list)
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("word"):
            by_word[row["word"]].append(row)
    return by_word


def wiki_url(headword, lang_name):
    """Le lien vers l'article du Wiktionnaire vietnamien dont vient l'entrée.

    Ancré sur la **langue**, pas sur la partie du discours, et c'est mesuré.
    MediaWiki numérote les titres qui se répètent dans une page : sur « chat »,
    qui existe en anglais, en créole, en irlandais et en français, les ancres
    sont « Danh_từ », « Danh_từ_2 », « Danh_từ_3 » — et la première appartient
    au **tiếng Anh**. Pointer « chat » (nom français) sur « #Danh_từ » enverrait
    donc le lecteur dans la section anglaise. Les ancres de langue, elles, sont
    uniques et stables : « #Tiếng_Pháp », « #Tiếng_Anh ».

    Il n'existe d'ancre par sens dans aucune édition du Wiktionnaire. Le lien
    mène à la section de la langue, où tous les sens sont listés — ce qui est
    ce qu'on veut pour vérifier une glose.
    """
    if not lang_name:
        return None
    page = urllib.parse.quote(headword.replace(" ", "_"), safe="_")
    anchor = urllib.parse.quote(lang_name.replace(" ", "_"), safe="_")
    return f"https://vi.wiktionary.org/wiki/{page}#{anchor}"


def build_senses(row):
    out = []
    for sense in row.get("senses", []):
        glosses = [clean(g) for g in sense.get("glosses", []) if clean(g)]
        if not glosses:
            continue
        examples = []
        for ex in sense.get("examples", []):
            src = clean(ex.get("text"))
            if not src:
                continue
            examples.append({"src": src, "vi": clean(ex.get("translation")) or None})
        out.append({
            "gloss": glosses[0],
            "sub": glosses[1:],
            "tags": [t for t in sense.get("tags", []) if t != "no-gloss"],
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


def build_entry(headword, rows, freq, code):
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
            # que pos : « Ngoại động từ » / « Nội động từ » là où pos dit
            # « verb ». C'est une information écrite pour un lecteur vietnamien.
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
        "id": f"{code}:{headword}",
        "lang": code,
        "headword": headword,
        # La section du Wiktionnaire d'où sort l'entrée — « Tiếng Pháp »,
        # « Tiếng Anh ». C'est kaikki qui la nomme, on ne la devine pas.
        "wiki": wiki_url(headword, (rows[0].get("lang") if rows else None)),
        "rank": freq.get(headword, 0.0),
        "ipa": list(dict.fromkeys(ipa))[:3],
        "audio": audio,
        "blocks": blocks,
        "derived": list(dict.fromkeys(derived)),
        "related": list(dict.fromkeys(related)),
        "synonyms": list(dict.fromkeys(syn)),
        "antonyms": list(dict.fromkeys(ant)),
    }


def apply_edits(entries, code):
    """base ⊕ edits. Le fichier est en git, la base n'y est pas.

    Une retouche est un patch de fusion par id : les clés présentes remplacent,
    les absentes laissent en place. Une retouche sans entrée de base crée une
    entrée — c'est comme ça que « faire », que le Wiktionnaire vietnamien n'a
    pas, entre dans le dictionnaire.
    """
    path = S.ROOT / "data" / f"edits-{code}.jsonl"
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
            patch.setdefault("lang", code)
            patch.setdefault("headword", eid.split(":", 1)[1])
            patch.setdefault("blocks", [])
            patch.setdefault("rank", 0.0)
            entries[eid] = patch
        else:
            base.update({k: v for k, v in patch.items() if k != "id"})
        entries[eid]["edited"] = True
        n += 1
    return n


def main():
    argv = sys.argv[1:]
    code = argv[argv.index("--lang") + 1] if "--lang" in argv else "fr"
    cfg = S.lang(code)
    top = 3000
    if "--top" in argv:
        top = int(argv[argv.index("--top") + 1])
    if "--all" in argv:
        top = None

    morph = importlib.import_module(cfg["morphology"])

    print(f"  {cfg['name']}")
    print("  lecture de kaikki…")
    by_word = load_kaikki(cfg["kaikki"])
    print(f"    {len(by_word):,} vedettes")

    # Les rattrapées, relues sur le wikitexte parce que wiktextract n'y voyait
    # aucune glose : « mélancolie », « dictionnaire », « Asie » — des mots que
    # le Wiktionnaire décrit bel et bien, mais en HTML brut. Elles complètent
    # une vedette existante, elles ne la remplacent pas.
    rescued_path = S.rescued(code)
    if rescued_path.exists():
        n_rescued = 0
        for line in open(rescued_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            by_word[row["word"]].append(row)
            n_rescued += 1
        print(f"    {n_rescued:,} blocs rattrapés sur le wikitexte")

    freq = morph.frequency()
    print(f"    {len(freq):,} lemmes classés par fréquence")

    # La coupe. Une vedette absente du classement a une fréquence de zéro et
    # passe donc en queue, ce qui est le bon comportement : ce sont les mots rares.
    ranked = sorted(by_word, key=lambda w: (-freq.get(w, 0.0), w))
    kept = ranked if top is None else ranked[:top]

    entries = {}
    for headword in kept:
        entry = build_entry(headword, by_word[headword], freq, code)
        if entry:
            entries[entry["id"]] = entry

    n_edits = apply_edits(entries, code)

    # La morphologie, après la coupe : on n'engendre que ce qui mène à une page.
    heads = {e["headword"] for e in entries.values()}
    kept_rows = {h: by_word.get(h, []) for h in heads}
    conjugated, stats = morph.build(kept_rows)
    print(f"    morphologie : {stats}")

    index = collections.defaultdict(list)
    for form, lemma, analysis in conjugated:
        if form != lemma and lemma in heads:
            index[form].append({"lemma": lemma, "analysis": analysis})

    # L'index à l'envers : lemme -> ses formes. Le construire une fois coûte un
    # parcours ; le redemander par entrée en coûtait autant que le produit des
    # deux tailles, et faisait passer la normalisation de secondes à minutes.
    by_lemma = collections.defaultdict(list)
    for form, targets in index.items():
        for target in targets:
            by_lemma[target["lemma"]].append(form)

    # La forme pronominale, quand la morphologie en a produit une. Lue dans
    # l'index plutôt que recalculée : l'élision dépend du h aspiré, que seul
    # Verbiste connaît, et deux endroits qui la décident finiraient par diverger.
    pronominal_of = {}
    for form, targets in index.items():
        for target in targets:
            if target.get("analysis") == "forme pronominale":
                pronominal_of[target["lemma"]] = form

    S.BUILD.mkdir(exist_ok=True)
    out = S.BUILD / f"lexicon-{code}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for entry in sorted(entries.values(), key=lambda e: -e["rank"]):
            entry["forms"] = sorted(by_lemma.get(entry["headword"], []),
                                    key=str.lower)
            pronominal = pronominal_of.get(entry["headword"])
            if pronominal:
                entry["pronominal"] = pronominal
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    (S.BUILD / f"forms-{code}.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")

    n_senses = sum(len(b["senses"]) for e in entries.values() for b in e["blocks"])
    n_ex = sum(len(s["examples"]) for e in entries.values()
               for b in e["blocks"] for s in b["senses"])
    print(f"\n  {len(entries):,} entrées, {n_senses:,} sens, {n_ex:,} exemples, "
          f"{len(index):,} formes fléchies indexées")
    if n_edits:
        print(f"  {n_edits} retouches appliquées")
    print(f"  → {out.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
