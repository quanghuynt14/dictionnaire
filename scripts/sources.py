#!/usr/bin/env python3
"""Où sont les sources, et ce qu'on en attend.

Un seul endroit pour les URL, les chemins et les licences. Le reste du
pipeline importe d'ici et ne connaît aucune adresse.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
BUILD = ROOT / "build"

# L'extraction de kaikki.org : le Wiktionnaire vietnamien, section « Tiếng Pháp ».
# C'est-à-dire des vedettes françaises glosées en vietnamien — exactement le sens
# de traduction qu'on veut, écrit par des humains, et déjà en JSON.
KAIKKI_FR_URL = (
    "https://kaikki.org/viwiktionary/Ti%E1%BA%BFng%20Ph%C3%A1p/"
    "kaikki.org-dictionary-Ti%E1%BA%BFngPh%C3%A1p.jsonl"
)
KAIKKI_FR = SOURCES / "kaikki-fr.jsonl"

# Lexique 3.83. Il ne donne pas un mot de vietnamien : il donne la morphologie,
# c'est-à-dire la seule chose qui sépare un dictionnaire d'une liste de vedettes.
# « allions » n'est pas dans le Wiktionnaire ; il est ici, avec son lemme et son
# analyse. Le fichier vient déjà du dépôt conjugaison, on le recopie.
LEXIQUE = SOURCES / "Lexique383.tsv"
LEXIQUE_FROM = ROOT.parent / "conjugaison" / "data" / "sources" / "Lexique383.tsv"

LOCK = ROOT / "data" / "sources.lock"

# Ce qui doit apparaître dans le bundle et sur le site. CC BY-SA veut dire deux
# choses : on cite, et ce qu'on en dérive se repartage aux mêmes conditions.
ATTRIBUTION = {
    "kaikki": "Wiktionnaire vietnamien (vi.wiktionary.org), extrait par "
              "wiktextract / kaikki.org — CC BY-SA 4.0",
    "lexique": "Lexique 3.83 (lexique.org), Boris New & Christophe Pallier — CC BY-SA 4.0",
}
