#!/usr/bin/env python3
"""Contrôle du XML produit, avant de le donner au compilateur d'Apple.

La panne qu'on cherche n'est pas un XML malformé — le DDK la voit et s'arrête.
C'est la vedette *vide*, la clé qui mène au mauvais mot, ou la forme fléchie
*absente* : rien ne les référence, rien ne s'en plaint, et elles ne se
manifestent que le jour où on cherche « allions » et où on n'obtient rien.

Usage :  python3 scripts/check.py [forme…]
"""

import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

import sources as S


D = "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}"
X = "{http://www.w3.org/1999/xhtml}"

# Ce qu'un dictionnaire français doit savoir faire, et que rien ne garantit :
# une forme fléchie très éloignée du lemme, un radical supplétif, un participe
# irrégulier, un pluriel, un féminin, et la vedette nue.
# Ce qu'un dictionnaire doit savoir faire, et que rien ne garantit : une forme
# très éloignée du lemme, un radical supplétif, un irrégulier, un pluriel, et
# la vedette nue. Les formes ambiguës y sont pour la raison qui a fait écrire
# les pages de forme : une clé mène à plusieurs mots, et tous doivent sortir.
PROBES = {
    "fr": ["allions", "allie", "prises", "assises", "irions", "vécu", "eu",
           "sois", "meilleures", "chats", "payions", "fussions", "aller",
           "allier", "langue", "beau",
           # Le pronominal : la forme que le lecteur a lue, et que le
           # Wiktionnaire range sous l'infinitif nu quand il la range.
           "se plaindre", "se défendre", "s'habiller", "se hisser",
           # Rattrapées du wikitexte, wiktextract n'y voyait aucune glose.
           "mélancolie", "dictionnaire"],
    "en": ["went", "children", "feet", "mice", "was", "ran", "better",
           "stopped", "carried", "going", "left", "saw", "book", "run",
           "good", "lying"],
}


def entries_of(xml):
    """Les entrées une par une, sans construire l'arbre entier."""
    for _, entry in ET.iterparse(xml, events=("end",)):
        if entry.tag != f"{D}entry":
            continue
        yield entry
        entry.clear()


def main():
    argv = sys.argv[1:]
    code = argv[argv.index("--lang") + 1] if "--lang" in argv else "fr"
    rest = [a for i, a in enumerate(argv)
            if a != "--lang" and (i == 0 or argv[i - 1] != "--lang")]
    XML = S.ROOT / "src" / f"{code}.xml"
    if not XML.exists():
        sys.exit(f"{XML} absent. Lancez d'abord `make xml LANG={code}`.")

    forms_index = json.load(open(S.BUILD / f"forms-{code}.json", encoding="utf-8"))
    wanted = set(rest or PROBES[code])

    problems = []
    ids = {}
    keys = collections.defaultdict(list)   # clé -> [vedette…]
    found = {}
    reachable = set()
    n_entries = n_keys = n_senses = 0

    for entry in entries_of(XML):
        n_entries += 1
        eid = entry.get("id")
        if eid in ids:
            problems.append(f"id « {eid} » réutilisé — deux entrées se recouvrent")
        ids[eid] = True

        head_el = entry.find(f".//{X}h1")
        head = (head_el.text or "").strip() if head_el is not None else ""
        if not head:
            problems.append(f"{eid} : entrée sans vedette")

        index_values = [n.get(f"{D}value") for n in entry.findall(f"{D}index")]
        if not index_values:
            problems.append(f"{eid} « {head} » : aucune clé — introuvable")
        n_keys += len(index_values)
        for value in index_values:
            keys[value].append(head)

        senses = entry.findall(f".//{X}li[@class='sense']")
        n_senses += len(senses)
        # Le tampon de fabrication n'a pas de sens, et c'est voulu.
        if not senses and eid != "e_about":
            problems.append(f"« {head} » : aucun sens — page vide")
        for sense in senses:
            gloss = sense.find(f"{X}span[@class='gloss']")
            if gloss is None or not (gloss.text or "").strip():
                problems.append(f"« {head} » : un sens sans glose")

        # Les mots que cette page couvre. Pour une entrée ordinaire c'est sa
        # vedette ; pour une page de forme ambiguë, c'est la liste de ses
        # membres — « allions » couvre aller et allier.
        members = [(m.text or "").strip()
                   for m in entry.findall(f".//{X}h2[@class='member-head']")]
        covers = members or ([head] if head else [])
        if index_values:
            reachable.update(covers)

        for form in wanted & set(index_values):
            found.setdefault(form, []).extend(covers)

    print(f"{n_entries} entrées, {len(keys)} clés distinctes, {n_senses} sens")

    # Depuis les pages de forme ambiguë, une clé n'appartient qu'à une entrée :
    # « allions » est la clé de sa propre page, et n'est plus sur aller ni sur
    # allier. Deux entrées pour une clé voudrait dire que le partage a fuité,
    # et la fenêtre de survol retomberait sur une seule des deux.
    for value, heads in keys.items():
        if len(heads) > 1:
            problems.append(f"la clé « {value} » est portée par {len(heads)} "
                            f"entrées — {heads[:4]}")

    # Toute vedette doit être atteignable. Elle l'est par sa propre clé, ou
    # parce qu'une page de forme ambiguë l'a absorbée : « brillant » est à la
    # fois un adjectif et le participe présent de « briller », donc sa clé vit
    # sur la page « brillant » qui porte les deux. Ce qu'on refuse, c'est le mot
    # que plus rien n'atteint.
    lexicon_heads = {json.loads(l)["headword"]
                     for l in open(S.BUILD / f"lexicon-{code}.jsonl", encoding="utf-8")
                     if l.strip()}
    orphans = sorted(lexicon_heads - reachable)
    if orphans:
        problems.append(f"{len(orphans)} vedettes qu'aucune clé n'atteint — "
                        f"{orphans[:6]}")

    print()
    for form in sorted(wanted):
        heads = found.get(form)
        if not heads:
            problems.append(f"« {form} » : aucune clé — introuvable dans Dictionary.app")
            print(f"  ✗ « {form} »")
            continue
        print(f"  ✓ « {form} » → {', '.join(heads)}")
        # Et l'index des formes doit être d'accord avec le XML. Les deux sont
        # produits par le même script, mais pas par le même chemin de code.
        expected = {x["lemma"] for x in forms_index.get(form, [])}
        if expected and not expected & set(heads):
            problems.append(
                f"« {form} » : le XML mène à {heads}, l'index annonçait {expected}")

    if problems:
        print()
        for problem in problems[:40]:
            print(f"  ✗ {problem}")
        if len(problems) > 40:
            print(f"  … et {len(problems) - 40} autres")
        sys.exit(1)
    print("\n  tout se tient")


if __name__ == "__main__":
    main()
