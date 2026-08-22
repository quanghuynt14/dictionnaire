#!/usr/bin/env python3
"""Interroge le dictionnaire installé par l'API dont se sert Dictionary.app.

`check.py` porte sur le XML : la clé est-elle écrite, mène-t-elle au bon mot ?
Celui-ci porte sur le bundle : la forme se retrouve-t-elle vraiment, et la page
contient-elle ce qu'on a voulu y mettre ? Entre les deux il y a le compilateur
d'Apple et un index trie que personne ne relit à l'œil.

Usage :  python3 scripts/verify_lookup.py [forme…]
"""

import ctypes
import ctypes.util
import json
import pathlib
import plistlib
import sys
import unicodedata

import sources as S

BUNDLE = pathlib.Path.home() / "Library/Dictionaries/Pháp-Việt.dictionary"
DEFAULT_FORMS = ["allions", "irions", "vécu", "eu", "sois", "meilleures",
                 "chats", "aller", "langue", "beau"]

cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
cs = ctypes.CDLL(ctypes.util.find_library("CoreServices"))

CFIndex = ctypes.c_int64
UTF8 = 0x08000100


class CFRange(ctypes.Structure):
    _fields_ = [("location", CFIndex), ("length", CFIndex)]


for fn, res, args in [
    (cf.CFStringCreateWithCString, ctypes.c_void_p,
     [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]),
    (cf.CFStringGetLength, CFIndex, [ctypes.c_void_p]),
    (cf.CFStringGetCString, ctypes.c_bool,
     [ctypes.c_void_p, ctypes.c_char_p, CFIndex, ctypes.c_uint32]),
    (cf.CFSetGetCount, CFIndex, [ctypes.c_void_p]),
    (cf.CFArrayGetCount, CFIndex, [ctypes.c_void_p]),
    (cf.CFArrayGetValueAtIndex, ctypes.c_void_p, [ctypes.c_void_p, CFIndex]),
    (cs.DCSCopyAvailableDictionaries, ctypes.c_void_p, []),
    # Sans restype déclaré, ctypes rend un c_int et tronque le pointeur.
    (cs.DCSGetActiveDictionaries, ctypes.c_void_p, []),
    (cs.DCSDictionaryGetName, ctypes.c_void_p, [ctypes.c_void_p]),
    (cs.DCSDictionaryGetIdentifier, ctypes.c_void_p, [ctypes.c_void_p]),
    (cs.DCSDictionaryGetPrimaryLanguage, ctypes.c_void_p, [ctypes.c_void_p]),
    (cs.DCSCopyRecordsForSearchString, ctypes.c_void_p, [ctypes.c_void_p] * 4),
    (cs.DCSRecordGetHeadword, ctypes.c_void_p, [ctypes.c_void_p]),
    (cs.DCSCopyTextDefinition, ctypes.c_void_p,
     [ctypes.c_void_p, ctypes.c_void_p, CFRange]),
]:
    fn.restype, fn.argtypes = res, args
cf.CFSetGetValues.argtypes = [ctypes.c_void_p, ctypes.c_void_p]


def fold(text):
    """Sans diacritiques : le pliage que le DDK applique aux clés supplémentaires."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower())
                   if not unicodedata.combining(c))


def cfstr(text):
    return cf.CFStringCreateWithCString(None, text.encode("utf-8"), UTF8)


def pystr(ref):
    if not ref:
        return None
    size = (cf.CFStringGetLength(ref) + 1) * 4
    buf = ctypes.create_string_buffer(size)
    if not cf.CFStringGetCString(ref, buf, size, UTF8):
        return None
    return buf.value.decode("utf-8")


def find_dictionary(identifier):
    """On demande la référence au système plutôt que de la fabriquer depuis l'URL.

    DCSDictionaryCreate() rend NULL même sur un bundle sain. Le système, lui,
    tient la liste des dictionnaires qu'il a indexés ; en faire partie est déjà
    la moitié du test. On cherche par identifiant et non par nom : le nom change
    dès qu'on touche à CFBundleDisplayName.
    """
    available = cs.DCSCopyAvailableDictionaries()
    count = cf.CFSetGetCount(available) if available else 0
    refs = (ctypes.c_void_p * count)()
    cf.CFSetGetValues(available, refs)
    for ref in refs:
        if pystr(cs.DCSDictionaryGetIdentifier(ref)) == identifier:
            return ref
    return None


def active_identifiers():
    active = cs.DCSGetActiveDictionaries()
    count = cf.CFSetGetCount(active) if active else 0
    refs = (ctypes.c_void_p * count)()
    cf.CFSetGetValues(active, refs)
    return {pystr(cs.DCSDictionaryGetIdentifier(r)) for r in refs}


def main():
    if not BUNDLE.exists():
        sys.exit(f"{BUNDLE} absent. Lancez `make install`.")

    identifier = plistlib.loads(
        (S.ROOT / "src" / "Info.plist").read_bytes())["CFBundleIdentifier"]
    dictionary = find_dictionary(identifier)
    if not dictionary:
        sys.exit(f"« {identifier} » n'est pas dans la liste du système. Le bundle "
                 "est installé mais macOS ne l'a pas indexé : relancez Dictionary.app.")

    lexicon = {}
    for line in open(S.BUILD / "lexicon.jsonl", encoding="utf-8"):
        entry = json.loads(line)
        lexicon[entry["headword"]] = entry
    forms_index = json.load(open(S.BUILD / "forms.json", encoding="utf-8"))

    problems = []
    print(f"  {pystr(cs.DCSDictionaryGetName(dictionary))}  [{identifier}]")

    if identifier not in active_identifiers():
        problems.append("le dictionnaire est installé mais pas coché : "
                        "Dictionary.app > Réglages, puis cochez-le")

    # Aucune langue déclarée, volontairement — mesuré dans conjugaison comme
    # dégradant le classement dans la fenêtre de consultation.
    language = pystr(cs.DCSDictionaryGetPrimaryLanguage(dictionary))
    print(f"  langue déclarée : {language or 'aucune (voulu)'}")
    if language:
        problems.append(f"langue « {language} » déclarée — mesurée comme "
                        "dégradant le classement")
    print()

    for form in sys.argv[1:] or DEFAULT_FORMS:
        records = cs.DCSCopyRecordsForSearchString(dictionary, cfstr(form), None, None)
        count = cf.CFArrayGetCount(records) if records else 0
        if not count:
            problems.append(f"« {form} » : aucun enregistrement")
            print(f"  ✗ « {form} »  introuvable")
            continue

        headwords = [pystr(cs.DCSRecordGetHeadword(cf.CFArrayGetValueAtIndex(records, i)))
                     for i in range(count)]

        # Le lemme attendu : ce que l'index des formes annonçait. Le bundle doit
        # ramener cette page-là, pas seulement *une* page.
        expected = {x["lemma"] for x in forms_index.get(form, [])} or {form}

        # DCSRecordGetHeadword ne rend pas la vedette de la page : il rend le
        # `d:title` de la *clé*, c'est-à-dire l'étiquette de la liste de
        # résultats. Pour une forme fléchie on l'écrit « allions (aller) », donc
        # comparer cette chaîne au lemme échoue toujours — ce qui a fait passer
        # sept recherches parfaitement bonnes pour des pannes.
        #
        # On reconstruit donc les étiquettes qu'on a nous-mêmes écrites, et
        # c'est le corps de la page, plus bas, qui sert de vraie preuve.
        labels = {h for h in expected} | {f"{form} ({h})" for h in expected}
        # Les clés supplémentaires du DDK plient les accents, pour que « vecu »
        # trouve « vécu ». L'effet de bord est qu'une recherche ramène ses
        # voisins sans accents : c'est utile, pas faux.
        if not labels & set(headwords):
            problems.append(f"« {form} » : le bundle ramène {headwords}, "
                            f"on attendait une étiquette parmi {sorted(labels)}")
            print(f"  ✗ « {form} » → {', '.join(headwords)}")
            continue

        # Dictionary.app rend la page en texte brut. On ne cherche pas à la
        # relire : on exige qu'une première glose s'y retrouve telle quelle.
        # C'est ce qui prouve que la page ouverte est une page qu'on a écrite,
        # et pas une voisine ramenée par le pliage des accents.
        #
        # « une » et non « celle de la vedette attendue », parce qu'une clé mène
        # légitimement à plusieurs pages : « vécu » est à la fois le participe de
        # vivre *et* une vedette à lui — adjectif « đã trải qua », nom « vốn
        # sống ». Le bundle rend les deux enregistrements, dans le bon ordre, et
        # DCSCopyTextDefinition n'en rend qu'un sans garantir lequel. Exiger
        # celui de vivre faisait échouer une recherche parfaitement juste.
        text = pystr(cs.DCSCopyTextDefinition(dictionary, cfstr(form),
                                              CFRange(0, len(form)))) or ""

        # Les vedettes que cette clé atteint : le lemme attendu, plus la forme
        # elle-même quand elle est aussi une vedette.
        candidates = list(expected) + ([form] if form in lexicon
                                       and form not in expected else [])

        def first_gloss(head):
            entry = lexicon.get(head)
            if entry and entry["blocks"] and entry["blocks"][0]["senses"]:
                return entry["blocks"][0]["senses"][0]["gloss"]
            return None

        glosses = {h: first_gloss(h) for h in candidates}
        hit = next((h for h, g in glosses.items() if g and g in text), None)

        mark = "✓"
        if not hit and any(glosses.values()):
            problems.append(
                f"« {form} » : la page rendue ne contient la première glose "
                f"d'aucune des vedettes atteintes ({', '.join(candidates)})")
            mark = "✗"

        head = next(iter(expected))
        how = next((x["analysis"] for x in forms_index.get(form, [])
                    if x["lemma"] == head), None)
        via = f"  ({how})" if how and form != head else ""
        # Le cas où la forme est aussi une vedette mérite d'être dit : c'est là
        # que la liste de résultats affiche deux lignes, et c'est voulu.
        aussi = f"  [aussi vedette]" if form in lexicon and form not in expected else ""
        print(f"  {mark} « {form} » → {head}   {glosses.get(head) or ''}{via}{aussi}")

    if problems:
        print()
        for problem in problems:
            print(f"  ✗ {problem}")
        sys.exit(1)
    print("\n  le bundle répond")


if __name__ == "__main__":
    main()
