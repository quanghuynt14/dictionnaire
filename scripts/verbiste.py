#!/usr/bin/env python3
"""Verbiste : le paradigme *complet* d'un verbe, engendré depuis un modèle.

Pourquoi il a fallu l'ajouter, alors que Lexique était déjà là. Lexique est une
base d'occurrences : il ne contient que les formes *attestées dans ses corpus*.
Mesuré sur ses 6 399 verbes — 10,1 formes en moyenne là où un paradigme français
en compte environ quarante-cinq, 56 % des verbes sous les dix formes, et huit
verbes seulement au complet. « allions » y est, sous aller ; il n'y est pas sous
allier, et « allier » n'a que treize formes en tout.

Un dictionnaire qu'on interroge en tapant la forme qu'on vient de lire ne peut
pas se contenter de ça. Verbiste, lui, est génératif : un modèle par famille, un
radical par verbe, et les quarante-cinq cases sortent — attestées ou non, ce qui
est exactement ce qu'on veut, puisque la question n'est pas « ce mot est-il
fréquent » mais « qu'est-ce que je viens de lire ».

Règle de partage qui en découle : **les formes verbales viennent de Verbiste et
de lui seul ; Lexique garde les noms, les adjectifs, et la fréquence.** Ce n'est
pas seulement une question de complétude — Lexique porte aussi des erreurs de
lemmatisation sur les verbes (il range la forme « allier » sous le lemme
« aller »), et les mélanger ferait entrer ces erreurs dans l'index.

Les temps composés ne sont pas engendrés : « nous avons allié » fait trois mots,
et d:value n'accepte pas l'espace. Ils ne sont pas perdus pour autant — leurs
deux morceaux, l'auxiliaire et le participe, sont chacun des formes simples.
"""

import xml.etree.ElementTree as ET

import sources as S

# Le nom Verbiste d'une case -> le code compact que sait lire analyse_verbe().
# L'ordre est celui d'une grammaire : on le garde, il devient celui de la page.
CASES = [
    (("Infinitif", "infinitif-présent"), "inf", None),
    (("Indicatif", "présent"), "ind:pre", 6),
    (("Indicatif", "imparfait"), "ind:imp", 6),
    (("Indicatif", "passé-simple"), "ind:pas", 6),
    (("Indicatif", "futur-simple"), "ind:fut", 6),
    (("Conditionnel", "présent"), "cnd:pre", 6),
    (("Subjonctif", "présent"), "sub:pre", 6),
    (("Subjonctif", "imparfait"), "sub:imp", 6),
    (("Imperatif", "imperatif-présent"), "imp:pre", 3),
    (("Participe", "participe-présent"), "par:pre", None),
    (("Participe", "participe-passé"), "par:pas", 4),
]

PERSONNES_6 = ["1s", "2s", "3s", "1p", "2p", "3p"]
# L'impératif n'a que trois personnes, et ce ne sont pas les trois premières.
PERSONNES_3 = ["2s", "1p", "2p"]
# Verbiste range le participe passé masculin singulier, masculin pluriel,
# féminin singulier, féminin pluriel — pas dans l'ordre des grammaires.
ACCORDS_PP = ["giống đực số ít", "giống đực số nhiều",
              "giống cái số ít", "giống cái số nhiều"]


def load_templates():
    """nom du modèle -> {(mode, temps): [[graphies…] par personne]}."""
    root = ET.parse(S.CONJUGATIONS).getroot()
    out = {}
    for template in root.findall("template"):
        cells = {}
        for mode in template:
            for tense in mode:
                # Un <p> peut porter plusieurs <i> — « paie » et « paye » — ou
                # aucun, quand la case n'existe pas pour ce modèle.
                cells[(mode.tag, tense.tag)] = [
                    [i.text for i in p.findall("i") if i.text]
                    for p in tense.findall("p")
                ]
        out[template.get("name")] = cells
    return out


def load_verbs():
    """infinitif -> nom du modèle."""
    root = ET.parse(S.VERBS).getroot()
    return {v.find("i").text: v.find("t").text
            for v in root.findall("v")
            if v.find("i") is not None and v.find("t") is not None}


def paradigm(infinitive, template_name, templates):
    """Toutes les formes simples d'un verbe -> [(forme, code d'analyse)].

    Le modèle se nomme « radical:terminaison » — « aim:er » pour allier. La
    terminaison dit combien de lettres retirer de l'infinitif pour obtenir le
    radical : allier moins « er » donne « alli », et « alli » + « ons » donne
    « allions », qui est précisément la forme que Lexique ne connaissait pas.
    """
    template = templates.get(template_name)
    if template is None:
        return []
    ending = template_name.split(":", 1)[1]
    stem = infinitive[:len(infinitive) - len(ending)]

    out = []
    for key, code, n_persons in CASES:
        cells = template.get(key) or []
        for position, spellings in enumerate(cells):
            if n_persons == 6:
                suffix = f":{PERSONNES_6[position]}" if position < 6 else ""
            elif n_persons == 3:
                suffix = f":{PERSONNES_3[position]}" if position < 3 else ""
            else:
                suffix = ""
            for spelling in spellings:
                form = stem + spelling
                if not form:
                    continue
                if code == "par:pas":
                    # Le participe passé s'accorde ; ce n'est pas une personne.
                    out.append((form, "par:pas", ACCORDS_PP[position]
                                if position < 4 else None))
                else:
                    out.append((form, code + suffix, None))
    return out


def build(headwords):
    """Les paradigmes des verbes qui sont des vedettes -> [(forme, lemme, code, accord)].

    On ne fabrique que ce qui mène quelque part. Le paradigme d'un verbe absent
    du dictionnaire produirait des clés vers une page qui n'existe pas.
    """
    templates = load_templates()
    verbs = load_verbs()
    out = []
    covered = 0
    for infinitive, template_name in verbs.items():
        if infinitive not in headwords:
            continue
        covered += 1
        for form, code, accord in paradigm(infinitive, template_name, templates):
            out.append((form, infinitive, code, accord))
    return out, covered, len(verbs)
