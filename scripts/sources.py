#!/usr/bin/env python3
"""Où sont les sources, ce qu'on en attend, et sous quelle licence.

Un seul endroit pour les URL, les chemins et les crédits. Le reste du pipeline
importe d'ici et ne connaît aucune adresse.

Deux dictionnaires en sortent — Pháp–Việt et Anh–Việt. Ils partagent tout le
code et rien de leurs sources : c'est `LANGS` qui les sépare, et c'est le seul
endroit où la différence est écrite.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
BUILD = ROOT / "build"
LOCK = ROOT / "data" / "sources.lock"

# Les deux fichiers Verbiste et Lexique viennent du dépôt voisin plutôt que du
# réseau : conjugaison les a déjà, et les deux projets doivent parler de la même
# morphologie. Deux copies d'un même fichier qui divergent, c'est un bug qu'on
# ne verrait jamais.
CONJUGAISON = ROOT.parent / "conjugaison" / "data" / "sources"

LANGS = {
    "fr": {
        "name": "Pháp–Việt",
        "bundle": "Pháp-Việt",
        # Le nom du bundle porte des accents ; celui de l'archive publiée ne
        # peut pas. GitHub remplace tout caractère non-ASCII d'un fichier de
        # version par un point : « Pháp-Việt.dictionary.zip » y devient
        # « Phap-Vi.t.dictionary.zip », et l'URL de téléchargement rend 404.
        "slug": "phap-viet",
        "identifier": "fr.huy.phap-viet",
        # La section « Tiếng Pháp » du Wiktionnaire vietnamien : des vedettes
        # françaises glosées en vietnamien, écrites par des humains, déjà en JSON.
        "kaikki_url": ("https://kaikki.org/viwiktionary/Ti%E1%BA%BFng%20Ph%C3%A1p/"
                       "kaikki.org-dictionary-Ti%E1%BA%BFngPh%C3%A1p.jsonl"),
        "kaikki": SOURCES / "kaikki-fr.jsonl",
        "morphology": "morph_fr",
        "credits": [
            "Wiktionnaire vietnamien (vi.wiktionary.org), extrait par "
            "wiktextract / kaikki.org — CC BY-SA 4.0",
            "Verbiste, Pierre Sarrazin (sarrazip.com), via verbecc de "
            "Brett Tolbert — GPL v2",
            "Lexique 3.83 (lexique.org), Boris New & Christophe Pallier — CC BY-SA 4.0",
        ],
    },
    "en": {
        "name": "Anh–Việt",
        "bundle": "Anh-Việt",
        "slug": "anh-viet",
        "identifier": "fr.huy.anh-viet",
        "kaikki_url": ("https://kaikki.org/viwiktionary/Ti%E1%BA%BFng%20Anh/"
                       "kaikki.org-dictionary-Ti%E1%BA%BFngAnh.jsonl"),
        "kaikki": SOURCES / "kaikki-en.jsonl",
        "morphology": "morph_en",
        "credits": [
            "Wiktionnaire vietnamien (vi.wiktionary.org), extrait par "
            "wiktextract / kaikki.org — CC BY-SA 4.0",
            "WordNet 3.0, Princeton University — licence WordNet",
            "SUBTLEX-US, Brysbaert & New — usage libre pour la recherche",
        ],
    },
}

# --- morphologie française --------------------------------------------------

LEXIQUE = SOURCES / "Lexique383.tsv"
VERBS = SOURCES / "verbs-fr.xml"
CONJUGATIONS = SOURCES / "conjugations-fr.xml"

# --- morphologie anglaise ---------------------------------------------------

# Les listes d'exceptions de WordNet : les irréguliers, à la main, et justes.
# Mesuré contre UniMorph, qui a l'air plus gros et qui rate « children », « was »,
# « feet », « geese », et range « ran » sous « rin ».
WORDNET_EXC = SOURCES / "wordnet-exc"
WORDNET_URL = ("https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/"
               "packages/corpora/wordnet.zip")

# SUBTLEX-US : la fréquence qui ordonne le dictionnaire anglais, comme Lexique
# ordonne le français. Même corpus de sous-titres, même idée.
SUBTLEX = SOURCES / "subtlex-us.txt"
SUBTLEX_URL = ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
               "master/content/2018/en/en_full.txt")


def rescued(code):
    """Les vedettes que wiktextract rend sans glose, relues sur le wikitexte.

    Une partie du Wiktionnaire vietnamien écrit ses définitions en HTML brut
    (`<LI class=def>`) ou sur une ligne indentée après un tiret, formes que
    wiktextract ne reconnaît pas. Voir scripts/rescue.py.
    """
    return SOURCES / f"rescued-{code}.jsonl"


def lang(code):
    if code not in LANGS:
        raise SystemExit(f"langue inconnue « {code} » — attendu : "
                         f"{', '.join(LANGS)}")
    return LANGS[code]
