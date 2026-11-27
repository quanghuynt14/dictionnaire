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


# Ce que build_entry lit d'une ligne kaikki. Le reste — head_templates,
# catégories, étymologie — pèse plus que les sens, et Việt–Pháp lit deux dumps.
KEPT_FIELDS = ("word", "lang", "pos", "pos_title", "tags", "senses", "sounds",
               "derived", "related", "synonyms", "antonyms")


def load_kaikki(sources, keep=None):
    """Les lignes kaikki de toutes les sources, regroupées par vedette.

    Chaque ligne garde la trace de sa source sous `_src` : c'est elle qui dit
    dans quelle langue sont ses gloses et vers quel wiki renvoyer. Les sources
    sont lues dans l'ordre de la liste, donc les blocs d'une vedette sortent
    dans cet ordre aussi — le français avant l'anglais pour Việt–Pháp.
    """
    by_word = collections.defaultdict(list)
    for src in sources:
        for line in open(src["path"], encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not row.get("word") or (keep and not keep(row)):
                continue
            if len(sources) > 1:
                row = {k: row[k] for k in KEPT_FIELDS if k in row}
            row["_src"] = src
            by_word[row["word"]].append(row)
    return by_word


def wiki_url(headword, lang_name, host="vi.wiktionary.org"):
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
    return f"https://{host}/wiki/{page}#{anchor}"


def build_senses(row, keep_sense=None):
    out = []
    for sense in row.get("senses", []):
        if keep_sense and not keep_sense(sense):
            continue
        glosses = [clean(g) for g in sense.get("glosses", []) if clean(g)]
        if not glosses:
            continue
        examples = []
        for ex in sense.get("examples", []):
            src = clean(ex.get("text"))
            if not src:
                continue
            # `tr` : la traduction de l'exemple, dans la langue des gloses —
            # le vietnamien pour Pháp–Việt, le français ou l'anglais pour
            # Việt–Pháp.
            examples.append({"src": src, "tr": clean(ex.get("translation")) or None})
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


def ipa_of(text):
    """La transcription, si elle en est une.

    Le Wiktionnaire vietnamien écrit /…/. Le français note la transcription
    phonologique entre barres obliques inverses, \\an˧˧\\, et l'anglais
    ne donne pour le vietnamien que la phonétique entre crochets, une par
    dialecte. On ramène les premières aux barres obliques ; les crochets
    restent tels quels, parce qu'ils ne disent pas la même chose.
    """
    text = text or ""
    if len(text) > 2 and text[0] == text[-1] == "\\":
        return f"/{text[1:-1]}/"
    return text if text[:1] in ("/", "[") else None


def build_entry(headword, rows, freq, code, morph=None):
    """Les lignes kaikki d'une même vedette -> une entrée, sections par catégorie."""
    blocks, ipa, audio = [], [], None
    derived, related, syn, ant = [], [], [], []
    keep_sense = getattr(morph, "keep_sense", None)
    label = getattr(morph, "label", None)
    phonetic = code == "vi"

    for row in rows:
        senses = build_senses(row, keep_sense)
        if not senses:
            continue
        src = row.get("_src") or {}
        blocks.append({
            "pos": row.get("pos") or "",
            # L'étiquette de la catégorie, pour le lecteur. Pour Pháp–Việt et
            # Anh–Việt, c'est le pos_title du Wiktionnaire vietnamien, plus fin
            # que pos : « Ngoại động từ » / « Nội động từ » là où pos dit
            # « verb ». Pour Việt–Pháp, une étiquette française. Le nom de la
            # clé date du temps où elle était toujours en vietnamien.
            "pos_vi": (label(row) if label else clean(row.get("pos_title"))) or None,
            # La langue des gloses du bloc : « vi », « fr » ou « en ».
            "gloss_lang": src.get("gloss", "vi"),
            "tags": row.get("tags", []),
            "senses": senses,
        })
        for sound in row.get("sounds", []):
            found = ipa_of(sound.get("ipa"))
            if found and (phonetic or found.startswith("/")):
                ipa.append(found)
            if audio is None and sound.get("mp3_url"):
                audio = sound["mp3_url"]
        derived += words_of(row.get("derived"))
        related += words_of(row.get("related"))
        syn += words_of(row.get("synonyms"))
        ant += words_of(row.get("antonyms"))

    if not blocks:
        return None

    hosts = []
    for row in rows:
        src = row.get("_src") or {}
        url = wiki_url(headword, src.get("section") or row.get("lang"),
                       src.get("host", "vi.wiktionary.org"))
        if url and url not in hosts and any(
                b for b in blocks if b["gloss_lang"] == src.get("gloss", "vi")):
            hosts.append(url)

    return {
        "id": f"{code}:{headword}",
        "lang": code,
        "headword": headword,
        # La section du Wiktionnaire d'où sort l'entrée — « Tiếng Pháp »,
        # « Tiếng Anh ». C'est kaikki qui la nomme, on ne la devine pas.
        "wiki": hosts[0] if hosts else None,
        # Việt–Pháp sort de deux wikis : chaque bloc doit pouvoir renvoyer
        # au sien.
        "wikis": hosts,
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
            patch["blocks"] = patch["blocks"] + patch.pop("add_blocks", [])
            patch.setdefault("rank", 0.0)
            entries[eid] = patch
        else:
            # `add_blocks` ajoute au lieu de remplacer : c'est ainsi qu'un mot
            # anglais reçoit un bloc français écrit par Claude sans perdre
            # ses sens vietnamiens. Le reste du patch remplace, comme avant.
            added = patch.get("add_blocks") or []
            # Un patch `blocks` écrit avant la troisième langue remplace les
            # sens vietnamiens ; il ne doit pas effacer l'anglais de
            # « faire » venu du Wiktionnaire anglais.
            if "blocks" in patch:
                home = "fr" if code == "vi" else "vi"
                added = added + [b for b in base.get("blocks", [])
                                 if b.get("gloss_lang", "vi") != home]
            base.update({k: v for k, v in patch.items() if k not in ("id", "add_blocks")})
            # Les sens vietnamiens d'abord : c'est la langue du dictionnaire.
            base["blocks"] = sorted(base.get("blocks", []) + added,
                                    key=lambda b: b.get("gloss_lang", "vi") != "vi")
        entries[eid]["edited"] = True
        n += 1
    return n


MEMO_KEYS = ("origin", "related", "tip")


def apply_memos(entries, code):
    """Les notes « pour retenir » : d'où vient le mot, ses voisins, un mémo.

    Elles vivent dans `data/memo-<langue>.jsonl`, une ligne par mot, écrites
    à la main ou par l'outil MCP `dico_meo`, et marquées `"by": "huy"` ou
    `"by": "claude"`. Un mot n'en a pas forcément : « aller » n'a rien à
    raconter, « morgue » si.
    Elles s'ajoutent à l'entrée sans rien remplacer — ni sens, ni marque
    `edited`, car le dictionnaire, lui, n'a pas changé.

    Une note sur une vedette absente est dite, pas avalée : c'est une faute de
    frappe dans l'id, ou un mot que la coupe `--top` a laissé dehors.
    """
    path = S.ROOT / "data" / f"memo-{code}.jsonl"
    if not path.exists():
        return 0, []
    n, orphans = 0, []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        row = json.loads(line)
        memo = {k: row[k].strip() for k in MEMO_KEYS if isinstance(row.get(k), str) and row[k].strip()}
        if not memo:
            continue
        entry = entries.get(row.get("id"))
        if entry is None:
            orphans.append(row.get("id"))
            continue
        entry["memo"] = memo
        n += 1
    return n, orphans


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
    by_word = load_kaikki(S.kaikki_sources(code), getattr(morph, "keep", None))
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

    # La troisième langue complète une vedette, elle n'en crée pas : un mot
    # que seul le Wiktionnaire anglais connaît n'a rien à faire dans
    # Pháp–Việt. Voir foreign.py.
    if any(src.get("attach") for src in S.kaikki_sources(code)):
        # Le Wiktionnaire vietnamien écrit parfois « soeur », « oeuvre » sans
        # ligature ; l'anglais, « sœur ». Les lignes anglaises rejoignent la
        # vedette vietnamienne au lieu d'être écartées comme orphelines.
        for word in [w for w in by_word if "œ" in w or "æ" in w]:
            plain = word.replace("œ", "oe").replace("æ", "ae")
            rows = by_word[word]
            if plain in by_word and all((r.get("_src") or {}).get("attach") for r in rows):
                by_word[plain].extend(rows)
                del by_word[word]
        before = len(by_word)
        # Une vedette que les retouches créent (« je », que le Wiktionnaire
        # vietnamien n'a pas) garde ses lignes de la troisième langue.
        created = set()
        edits = S.ROOT / "data" / f"edits-{code}.jsonl"
        if edits.exists():
            for line in open(edits, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("//"):
                    created.add(json.loads(line).get("id", "").split(":", 1)[-1])
        by_word = collections.defaultdict(list, {
            w: rows for w, rows in by_word.items()
            if w in created or any(not (r.get("_src") or {}).get("attach") for r in rows)})
        print(f"    {before - len(by_word):,} vedettes de la troisième langue seule, écartées")

    freq = morph.frequency()
    print(f"    {len(freq):,} lemmes classés par fréquence")

    # Une langue peut réunir des vedettes que kaikki sépare — en vietnamien,
    # « thuỷ » et « thủy », deux places du même ton.
    if hasattr(morph, "merge"):
        before = len(by_word)
        by_word = morph.merge(by_word, freq)
        print(f"    {before - len(by_word):,} vedettes fusionnées")

    # La coupe. Une vedette absente du classement a une fréquence de zéro et
    # passe donc en queue, ce qui est le bon comportement : ce sont les mots rares.
    ranked = sorted(by_word, key=lambda w: (-freq.get(w, 0.0), w))
    kept = ranked if top is None else ranked[:top]

    entries = {}
    for headword in kept:
        entry = build_entry(headword, by_word[headword], freq, code, morph)
        if entry:
            entries[entry["id"]] = entry

    n_edits = apply_edits(entries, code)
    n_memos, memo_orphans = apply_memos(entries, code)

    # La morphologie, après la coupe : on n'engendre que ce qui mène à une page.
    heads = {e["headword"] for e in entries.values()}
    kept_rows = {h: by_word.get(h, []) for h in heads}
    conjugated, stats = morph.build(
        {h: [{k: v for k, v in r.items() if k != "_src"} for r in rows]
         for h, rows in kept_rows.items()})
    print(f"    morphologie : {stats}")

    index = collections.defaultdict(list)
    for form, lemma, analysis in conjugated:
        if form != lemma and lemma in heads:
            index[form].append({"lemma": lemma, "analysis": analysis})

    # Les renvois : une vedette dont le seul sens était « autre forme de X »
    # n'a pas de page, mais elle mène encore à X.
    if hasattr(morph, "redirects"):
        for form, lemma, analysis in morph.redirects(by_word):
            if lemma in heads and form not in heads and all(
                    t["lemma"] != lemma for t in index[form]):
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
    if n_memos:
        print(f"  {n_memos} notes pour retenir")
    if memo_orphans:
        print(f"  ⚠ notes sans vedette : {memo_orphans[:10]}")
    print(f"  → {out.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
