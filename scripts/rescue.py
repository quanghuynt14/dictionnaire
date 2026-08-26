#!/usr/bin/env python3
"""Récupère les vedettes que wiktextract rend sans aucune glose.

## Le problème

kaikki lit les définitions écrites en syntaxe MediaWiki — les lignes qui
commencent par `#`. Une partie du Wiktionnaire vietnamien ne les écrit pas
ainsi : l'import du Free Vietnamese Dictionary Project (`{{R:FVDP}}`) a posé
des `<LI class=def>` en HTML brut, et d'autres pages mettent la définition sur
une ligne indentée avec un tiret. wiktextract ne reconnaît ni l'un ni l'autre
et rend un sens vide, marqué `no-gloss`.

`normalize.py` écarte une entrée sans glose — à raison, une page vide n'est pas
une entrée. Mais ces pages-là ne sont pas vides : elles sont mal balisées. Le
mot y est, la traduction aussi, et le lecteur qui cherche « mélancolie » ou
« dictionnaire » ne trouvait rien.

Mesuré : 197 vedettes françaises (0,43 %) et 75 anglaises (0,06 %).

## Ce qu'on fait

On relit le wikitexte de ces pages-là — quelques centaines, par paquets de
quarante — et on en tire les gloses selon les formes rencontrées. Ce qui reste
illisible est compté et nommé, pas passé sous silence : certaines de ces pages
n'ont réellement aucune définition, seulement des exemples, et là c'est le
Wiktionnaire qui est vide, pas notre lecture.

Usage :  python3 scripts/rescue.py --lang fr
"""

import collections
import html as html_mod
import json
import re
import sys
import time
import urllib.parse
import urllib.request

import sources as S

API = "https://vi.wiktionary.org/w/api.php"
# Wikimedia refuse une requête sans agent descriptif — 403 sec.
UA = "dictionnaire/0.2 (https://github.com/quanghuynt14/dictionnaire) python-urllib"
BATCH = 40

# Le marqueur de section de langue, par code de dictionnaire. Le Wiktionnaire
# vietnamien emploie les deux formes, ISO-639-1 et -2.
LANG_MARKERS = {"fr": ("fra", "fr"), "en": ("eng", "en")}

# Les marqueurs qui ne sont *pas* une langue. Tout autre {{-xxx-}} referme la
# section : sans cette liste, on lirait la section vietnamienne d'une page
# bilingue et on collerait ses gloses sous la vedette française.
SECTIONS = {
    "pron", "etym", "syn", "ant", "ref", "drv", "trans", "rel", "related",
    "usage", "note", "see", "hom", "anagr", "der", "quot", "expr",
}
POS_OF = {
    "noun": "noun", "proper": "name", "pn": "name",
    "verb": "verb", "tr-verb": "verb", "intr-verb": "verb", "refl-verb": "verb",
    "adj": "adj", "adv": "adv", "prep": "prep", "conj": "conj",
    "pron-word": "pron", "interj": "intj", "intj": "intj", "num": "num",
    "abbr": "abbrev",
}


def clean(text):
    """Le wikitexte -> du texte lisible.

    On enlève les liens, le gras, les modèles et les entités. Ce qui reste est
    la glose telle qu'un lecteur la voit sur la page.
    """
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text).strip(" \t:;–—-")


def language_section(wikitext, code):
    """Le morceau de la page qui parle de notre langue, et lui seul."""
    markers = LANG_MARKERS[code]
    start = None
    for marker in markers:
        m = re.search(r"\{\{-" + marker + r"-\}\}", wikitext)
        if m:
            start = m.end()
            break
    if start is None:
        return None

    rest = wikitext[start:]
    for m in re.finditer(r"\{\{-([a-z-]{2,10})-\}\}", rest):
        name = m.group(1)
        if name not in SECTIONS and name not in POS_OF:
            return rest[:m.start()]
    return rest


def senses_from(section):
    """Les gloses d'une section, par categorie grammaticale.

    Voir `extract` pour les quatre formes rencontrees.
    """
    blocks = []
    parts = re.split(r"\{\{-([a-z-]{2,12})-\}\}", section)
    # parts = [avant, nom1, corps1, nom2, corps2, …]
    chunks = [(None, parts[0])] if parts[0].strip() else []
    for i in range(1, len(parts) - 1, 2):
        chunks.append((parts[i], parts[i + 1]))

    for name, body in chunks:
        pos = POS_OF.get(name or "", "noun" if name is None else None)
        if pos is None:
            continue
        glosses = extract(body)
        if glosses:
            blocks.append((pos, glosses))

    # La glose peut etre posee hors de son bloc : sur « Altaic », la definition
    # arrive apres {{-pron-}} alors qu'elle appartient a {{-adj-}}. Si aucun
    # bloc n'a rien donne, on relit — mais **seulement** les morceaux qui
    # peuvent porter une definition.
    #
    # Relire la section entiere etait faux : les definitions d'« IMHO » sont
    # des modeles qui se nettoient a vide, et le repli ramassait alors les
    # puces de {{-drv-}} — il rendait « IMNSHO, IMAO » comme sens d'IMHO.
    # Une glose fausse est pire qu'une glose absente.
    if not blocks:
        # Les formes non ambigues sur toute la section : sur « Altaic », le `#`
        # est pose sous {{-pron-}} alors qu'il appartient a {{-adj-}}, et un `#`
        # n'est jamais une liste de synonymes.
        glosses = extract(section, allow_bullets=False)
        if not glosses:
            bearing = "\n".join(
                body for name, body in chunks
                if name is None or name not in SECTIONS
            )
            glosses = extract(bearing)
        if glosses:
            first = next((POS_OF[n] for n, _ in chunks if n in POS_OF), "noun")
            blocks.append((first, glosses))

    return blocks


def dash_glosses(body):
    """La definition posee sur une ligne indentee, apres un tiret.

    On nettoie **avant** de couper au tiret, jamais l'inverse : le modele
    {{g-old|f}} contient un tiret, et couper d'abord donnait
    « old|f}} – Châu Á » comme glose d'« Asie ».
    """
    out = []
    for line in re.findall(r"^:\s*'{3}[^']+'{3}([^\n]*)", body, re.M):
        # Les modeles d'abord, parce que {{g-old|f}} porte un tiret et qu'on
        # couperait dessus. Le nettoyage complet vient apres la coupe : il
        # rogne les tirets de bord, donc l'appliquer avant ne laisserait plus
        # rien a couper — c'est ce qui faisait disparaitre « dictionnaire ».
        raw = re.sub(r"\{\{[^}]*\}\}", "", line)
        parts = re.split(r"\s*(?:&ndash;|[–—])\s*", raw, maxsplit=1)
        if len(parts) == 2:
            gloss = clean(parts[1])
            if gloss:
                out.append(gloss)
    return out


def extract(body, allow_bullets=True):
    """Les gloses d'un corps. Quatre formes, essayees dans cet ordre :

      1. <LI class=def> glose   — l'import FVDP, en HTML brut. La majorite.
      2. :'''mot''' – glose     — ligne indentee, tiret « – », « — » ou &ndash;.
      3. # glose                — la syntaxe normale, quand wiktextract l'a
                                  ratee pour une autre raison.
      4. * glose                — une puce, chez quelques pages anciennes.

    Une seule forme est retenue : si la premiere donne quelque chose, on ne
    ramasse pas en plus les puces d'une liste de synonymes.
    """
    forms = [
        [clean(g) for g in re.findall(r"<LI\s+class=def>([^\n]*)", body, re.I)],
        dash_glosses(body),
        [clean(g) for g in re.findall(r"^#(?![:*])\s*([^\n]*)", body, re.M)],
    ]
    # La puce est la seule forme ambigue : une liste de synonymes ou de derives
    # en porte aussi. On ne l'accepte que dans un bloc dont on sait qu'il porte
    # une definition — voir le repli de senses_from.
    if allow_bullets:
        forms.append([clean(g) for g in re.findall(r"^\*\s*([^\n]*)", body, re.M)])

    for candidates in forms:
        kept = [g for g in candidates if g]
        if kept:
            return kept
    return []


def fetch(titles):
    url = API + "?" + urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "format": "json", "titles": "|".join(titles),
    })
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    out = {}
    for page in data.get("query", {}).get("pages", {}).values():
        revisions = page.get("revisions")
        if revisions:
            out[page["title"]] = revisions[0]["slots"]["main"]["*"]
    return out


def main():
    argv = sys.argv[1:]
    code = argv[argv.index("--lang") + 1] if "--lang" in argv else "fr"
    cfg = S.lang(code)

    by_word = collections.defaultdict(list)
    for line in open(cfg["kaikki"], encoding="utf-8"):
        row = json.loads(line)
        by_word[row["word"]].append(row)

    missing = sorted(
        word for word, rows in by_word.items()
        if not any(s.get("glosses") for r in rows for s in r.get("senses", []))
    )
    print(f"  {len(missing)} vedettes sans glose dans le dump")

    pages = {}
    for i in range(0, len(missing), BATCH):
        pages.update(fetch(missing[i:i + BATCH]))
        time.sleep(0.3)
    print(f"  {len(pages)} pages relues")

    out = S.SOURCES / f"rescued-{code}.jsonl"
    rescued = 0
    still = []
    with open(out, "w", encoding="utf-8") as f:
        for word in missing:
            section = language_section(pages.get(word, ""), code)
            blocks = senses_from(section) if section else []
            if not blocks:
                still.append(word)
                continue
            rescued += 1
            for pos, glosses in blocks:
                f.write(json.dumps({
                    "word": word, "lang_code": code,
                    "lang": "Tiếng Pháp" if code == "fr" else "Tiếng Anh",
                    "pos": pos,
                    "senses": [{"glosses": [g]} for g in glosses],
                    "rescued": True,
                }, ensure_ascii=False) + "\n")

    print(f"\n  {rescued} récupérées, {len(still)} toujours sans glose")
    if still:
        print(f"  restantes : {', '.join(still[:12])}"
              f"{' …' if len(still) > 12 else ''}")
        print("  (ces pages n'ont réellement pas de définition, ou une forme"
              " qu'on ne lit pas encore)")
    print(f"  → {out.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
