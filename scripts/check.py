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

XML = S.ROOT / "src" / "phap-viet.xml"
D = "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}"
X = "{http://www.w3.org/1999/xhtml}"

# Ce qu'un dictionnaire français doit savoir faire, et que rien ne garantit :
# une forme fléchie très éloignée du lemme, un radical supplétif, un participe
# irrégulier, un pluriel, un féminin, et la vedette nue.
DEFAULT_FORMS = ["allions", "irions", "vécu", "eu", "sois", "meilleures",
                 "chats", "aller", "langue", "beau"]


def entries_of(xml):
    """Les entrées une par une, sans construire l'arbre entier."""
    for _, entry in ET.iterparse(xml, events=("end",)):
        if entry.tag != f"{D}entry":
            continue
        yield entry
        entry.clear()


def main():
    if not XML.exists():
        sys.exit(f"{XML} absent. Lancez d'abord `make xml`.")

    forms_index = json.load(open(S.BUILD / "forms.json", encoding="utf-8"))
    wanted = set(sys.argv[1:] or DEFAULT_FORMS)

    problems = []
    ids = {}
    keys = collections.defaultdict(list)   # clé -> [vedette…]
    found = {}
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

        # La vedette doit être sa propre clé. Sinon la page existe et personne
        # ne peut y arriver en tapant le mot lui-même.
        if head and head not in index_values and eid != "e_about":
            problems.append(f"« {head} » : la vedette n'est pas une clé")

        for form in wanted & set(index_values):
            found.setdefault(form, []).append(head)

    print(f"{n_entries} entrées, {len(keys)} clés distinctes, {n_senses} sens")

    # Une clé peut légitimement mener à plusieurs vedettes — « sois » est de
    # « être », « suis » est de « être » *et* de « suivre ». Ce qu'on refuse,
    # c'est la clé qui mène deux fois à la même vedette : la liste de résultats
    # afficherait alors deux lignes identiques.
    for value, heads in keys.items():
        if len(heads) != len(set(heads)):
            problems.append(f"la clé « {value} » mène deux fois à {set(heads)}")

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
