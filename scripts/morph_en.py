#!/usr/bin/env python3
"""Morphologie anglaise : forme fléchie -> vedette, en trois couches.

Le problème est le même qu'en français et la réponse est de la même forme. Le
dump kaikki contient **8 014 formes fléchies pour 119 166 vedettes** : autant
dire aucune. Chercher « went » dans un dictionnaire qui ne connaît que « go »
ne donne rien, et « went » est exactement ce qu'on tape en lisant.

Trois couches, par ordre d'autorité décroissante. Une couche ne corrige jamais
la précédente ; elle comble ce que la précédente n'a pas dit.

  1. **Les exceptions de WordNet** — 5 940 formes, à la main, et justes.
     C'est la couche des irréguliers : went, children, was, feet, geese, mice.
     Mesuré contre UniMorph, qui a l'air plus gros — 189 780 formes — et qui
     rate « children », « was », « were », « feet », « geese », et range « ran »
     sous « rin », un verbe dialectal rare. C'est la leçon de Lexique une
     seconde fois : une base d'occurrences n'est pas une liste d'irréguliers,
     et le volume ne dit rien de la justesse.

  2. **Les formes déclarées par l'entrée kaikki.** Peu nombreuses, mais quand
     le Wiktionnaire prend la peine d'écrire le pluriel, c'est qu'il sort de
     l'ordinaire.

  3. **Les règles.** L'équivalent de Verbiste : génératif, donc complet, donc
     indépendant de ce qu'un corpus a rencontré. L'anglais s'y prête bien mieux
     que le français — cinq cases, pas quarante-cinq, et une orthographe qui
     obéit.

Ce qu'on ne fait pas : redoubler la consonne finale des mots longs. « stop » →
« stopped » se décide sur l'accent tonique, que rien ici ne connaît, et
« visitted » serait une clé fausse. On double sur les monosyllabes, où la règle
est sûre ; ailleurs on s'abstient, et WordNet rattrape les irréguliers.
"""

import collections
import json
import re

import sources as S

VOWELS = "aeiou"

# Ce que porte chaque case. L'analyse ne s'affiche plus dans les pages — elle
# sert au contrôle et à la seed Mongo — mais elle reste écrite : une forme sans
# analyse est une forme qu'on ne peut plus vérifier.
LABELS = {
    "pl": "số nhiều",
    "3sg": "ngôi 3 số ít, thì hiện tại",
    "ing": "present participle",
    "ed": "past tense, past participle",
    "cmp": "so sánh hơn",
    "sup": "so sánh nhất",
}

# Les catégories kaikki qui reçoivent quelles cases.
SLOTS = {
    "noun": ["pl"],
    "name": ["pl"],
    "verb": ["3sg", "ing", "ed"],
    "adj": ["cmp", "sup"],
    "adv": ["cmp", "sup"],
}


def sibilant(word):
    """Les finales qui appellent « es » plutôt que « s » : box, church, kiss."""
    return word.endswith(("s", "x", "z", "ch", "sh"))


def consonant_y(word):
    return len(word) > 1 and word.endswith("y") and word[-2] not in VOWELS


def monosyllabic_cvc(word):
    """Consonne-voyelle-consonne, sur un mot court : la règle du redoublement.

    Restreinte aux mots d'une syllabe apparente, parce qu'au-delà c'est l'accent
    tonique qui décide — « prefer » redouble, « offer » non — et l'accent n'est
    écrit nulle part ici. Sur un monosyllabe la question ne se pose pas.
    """
    if len(word) < 3 or len(word) > 5:
        return False
    a, b, c = word[-3], word[-2], word[-1]
    if c in "wxy":
        return False
    # Une seule zone de voyelles : « stop » oui, « sleep » non (deux e), et
    # « visit » non plus, qui en a deux séparées.
    groups = re.findall(r"[aeiou]+", word)
    return (len(groups) == 1 and a not in VOWELS and b in VOWELS
            and c not in VOWELS)


def plural(word):
    if consonant_y(word):
        return [word[:-1] + "ies"]
    if sibilant(word):
        return [word + "es"]
    # « potato » fait « potatoes », « radio » fait « radios », et rien dans la
    # graphie ne les sépare. On rend les deux : une clé de trop ne coûte qu'un
    # peu de place, une clé manquante coûte une recherche qui ne trouve rien.
    if word.endswith("o") and len(word) > 2 and word[-2] not in VOWELS:
        return [word + "es", word + "s"]
    return [word + "s"]


def ing(word):
    if word.endswith("ie"):
        return [word[:-2] + "ying"]          # lie -> lying
    if word.endswith("e") and not word.endswith(("ee", "oe", "ye")):
        return [word[:-1] + "ing"]
    if monosyllabic_cvc(word):
        return [word + word[-1] + "ing"]
    return [word + "ing"]


def ed(word):
    if consonant_y(word):
        return [word[:-1] + "ied"]
    if word.endswith("e"):
        return [word + "d"]
    if monosyllabic_cvc(word):
        return [word + word[-1] + "ed"]
    return [word + "ed"]


def comparative(word, suffix):
    """suffix vaut « er » ou « est »."""
    if consonant_y(word):
        return [word[:-1] + "i" + suffix]
    if word.endswith("e"):
        return [word + suffix[1:]]
    if monosyllabic_cvc(word):
        return [word + word[-1] + suffix]
    return [word + suffix]


RULES = {
    "pl": plural,
    "3sg": plural,                            # même orthographe que le pluriel
    "ing": ing,
    "ed": ed,
    "cmp": lambda w: comparative(w, "er"),
    "sup": lambda w: comparative(w, "est"),
}


# Quelle case chaque fichier d'exceptions rend irrégulière. Un verbe irrégulier
# l'est à son passé, pas à son « -ing » : « go » fait « went » mais « going »,
# et « sleep » fait « slept » mais « sleeps ». On ne supprime donc que la case
# que WordNet a réellement remplie.
IRREGULAR_SLOTS = {
    "noun": ["pl"],
    "verb": ["ed"],
    "adj": ["cmp", "sup"],
    "adv": ["cmp", "sup"],
}


def frequency():
    """lemme -> fréquence. Le classement qui ordonne le dictionnaire.

    Même idée que Lexique côté français : un corpus de sous-titres, donc de la
    langue parlée, ce qui est le bon biais pour un dictionnaire qu'on ouvre en
    lisant ou en écoutant. Le fichier donne des occurrences brutes ; on les
    garde telles quelles, seul l'ordre compte.
    """
    freq = {}
    if not S.SUBTLEX.exists():
        return freq
    for line in open(S.SUBTLEX, encoding="utf-8", errors="replace"):
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            freq[parts[0]] = float(parts[1])
        except ValueError:
            continue
    return freq


def load_wordnet():
    """(forme -> {lemme}, {(lemme, case) déjà remplies par un irrégulier}).

    Le second ensemble sert à taire la règle. Sans lui on écrivait « goed » à
    côté de « went », « maked » à côté de « made » : des clés que personne ne
    tape, et surtout des clés qui peuvent percuter un vrai mot et fabriquer une
    page de forme ambiguë entre deux mots sans rapport.
    """
    forms = collections.defaultdict(set)
    filled = set()
    for name in ("noun", "verb", "adj", "adv"):
        path = S.WORDNET_EXC / f"{name}.exc"
        if not path.exists():
            continue
        for line in open(path, encoding="utf-8"):
            parts = line.split()
            if len(parts) < 2:
                continue
            for lemma in parts[1:]:
                forms[parts[0]].add(lemma)
                for slot in IRREGULAR_SLOTS[name]:
                    filled.add((lemma, slot))
    return forms, filled


def build(entries_by_head):
    """{vedette: [lignes kaikki]} -> [(forme, lemme, analyse)].

    On ne fabrique que ce qui mène quelque part : la forme d'un mot absent du
    dictionnaire produirait une clé vers une page qui n'existe pas.
    """
    wordnet, irregular = load_wordnet()
    out = []
    seen = set()

    def emit(form, lemma, label):
        if form == lemma or not form or " " in form:
            return
        if (form, lemma) in seen:
            return
        seen.add((form, lemma))
        out.append((form, lemma, label))

    # 1. WordNet, en premier : c'est la couche qui a raison quand elles divergent.
    n_wordnet = 0
    for form, lemmas in wordnet.items():
        for lemma in lemmas:
            if lemma in entries_by_head:
                emit(form, lemma, "dạng bất quy tắc")
                n_wordnet += 1

    # 2. Ce que l'entrée elle-même déclare.
    n_stated = 0
    for head, rows in entries_by_head.items():
        for row in rows:
            for form in row.get("forms") or []:
                text = (form.get("form") or "").strip()
                if not text or text == head:
                    continue
                tags = (form.get("tags") or []) + (form.get("raw_tags") or [])
                # « canonical » et « alternative » ne sont pas des flexions :
                # c'est la vedette réécrite, ou une variante orthographique.
                if "canonical" in tags or "romanization" in tags:
                    continue
                emit(text, head, ", ".join(tags) or "dạng khác")
                n_stated += 1

    # 3. Les règles, pour tout le reste.
    n_rules = 0
    for head, rows in entries_by_head.items():
        if " " in head or not head.isascii() or not head.islower():
            continue
        slots = set()
        for row in rows:
            slots.update(SLOTS.get(row.get("pos") or "", []))
        for slot in slots:
            # WordNet a déjà rempli cette case avec un irrégulier : la règle
            # n'aurait plus qu'à écrire une faute.
            if (head, slot) in irregular:
                continue
            for form in RULES[slot](head):
                before = len(seen)
                emit(form, head, LABELS[slot])
                n_rules += len(seen) - before

    return out, {"wordnet": n_wordnet, "kaikki": n_stated, "règles": n_rules}
