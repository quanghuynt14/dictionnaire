#!/usr/bin/env python3
"""Où sont les sources, ce qu'on en attend, et sous quelle licence.

Un seul endroit pour les URL, les chemins et les crédits. Le reste du pipeline
importe d'ici et ne connaît aucune adresse.

Quatre dictionnaires en sortent — Pháp–Việt, Anh–Việt, Việt–Pháp et Trung–Việt. Ils
partagent tout le code et rien de leurs sources : c'est `LANGS` qui les sépare,
et c'est le seul endroit où la différence est écrite.
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

# Le Wiktionnaire anglais, section vietnamienne. Việt–Pháp y lit des sens ;
# Trung–Việt y lit les lectures Hán Việt des sinogrammes. Un seul fichier.
VIETNAMESE_EN = {
    "key": "kaikki-vi-en", "gloss": "en",
    "host": "en.wiktionary.org", "section": "Vietnamese",
    "url": ("https://kaikki.org/dictionary/Vietnamese/"
            "kaikki.org-dictionary-Vietnamese.jsonl"),
    "path": SOURCES / "kaikki-vi-en.jsonl",
}

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
    # Le sens inverse : des vedettes vietnamiennes, glosées en français.
    #
    # Deux Wiktionnaires, et l'ordre compte. Le français d'abord : c'est la
    # langue du dictionnaire. L'anglais ensuite, tel quel et marqué EN, parce
    # que le Wiktionnaire anglais connaît deux fois plus de mots vietnamiens
    # (36 489 contre 15 543, mesuré le 2026-11-20) et parce que ses sens sont
    # souvent plus actuels — « tham nhũng » y est « to be corrupt », là où le
    # français dit « Tracassier et cupide ».
    #
    # On ne traduit pas l'anglais en français. Ce serait une traduction
    # automatique, que personne n'a écrite et que personne ne peut corriger
    # sur un wiki.
    "vi": {
        "name": "Việt–Pháp",
        "bundle": "Việt-Pháp",
        "slug": "viet-phap",
        "identifier": "fr.huy.viet-phap",
        "kaikki_sources": [
            {"key": "kaikki-vi-fr", "gloss": "fr",
             "host": "fr.wiktionary.org", "section": "Vietnamien",
             "url": ("https://kaikki.org/frwiktionary/Vietnamien/"
                     "kaikki.org-dictionary-Vietnamien.jsonl"),
             "path": SOURCES / "kaikki-vi-fr.jsonl"},
            VIETNAMESE_EN,
        ],
        # rescue.py relit le wikitexte du Wiktionnaire *vietnamien*. Ici les
        # deux sources sont d'autres éditions : il n'a rien à y faire.
        "rescue": False,
        "morphology": "morph_vi",
        "credits": [
            "Wiktionnaire français (fr.wiktionary.org), extrait par "
            "wiktextract / kaikki.org — CC BY-SA 4.0",
            "Wiktionary anglais (en.wiktionary.org), extrait par "
            "wiktextract / kaikki.org — CC BY-SA 4.0",
            "FrequencyWords, Hermit Dave, d'après OpenSubtitles — CC BY-SA 4.0",
        ],
    },
    # Des vedettes chinoises (mandarin), glosées en vietnamien.
    #
    # Même méthode que Việt–Pháp : le Wiktionnaire vietnamien d'abord, c'est
    # la langue du dictionnaire ; l'anglais ensuite, tel quel et marqué EN.
    # Le vietnamien n'a que 7 000 mots chinois, l'anglais 300 000 lignes.
    #
    # Deux sections du Wiktionnaire vietnamien, parce que le wiki en a deux :
    # « Tiếng Quan Thoại » (le mandarin, l'ancienne) et « Tiếng Trung Quốc »
    # (le chinois, la nouvelle, alignée sur l'anglais).
    #
    # Le dump anglais pèse 1,2 Go. fetch.py le filtre pendant qu'il arrive
    # (`slim`) : on ne garde que le mandarin et les champs lus ici.
    #
    # `optional` : `fetch.py` sans --lang ne le télécharge pas. Le lexique
    # de reindoo n'a pas à payer ce dump tant qu'il ne s'en sert pas.
    "zh": {
        "name": "Trung–Việt",
        "bundle": "Trung-Việt",
        "slug": "trung-viet",
        "identifier": "fr.huy.trung-viet",
        "optional": True,
        "kaikki_sources": [
            {"key": "kaikki-zh-cmn", "gloss": "vi",
             "host": "vi.wiktionary.org", "section": "Tiếng Quan Thoại",
             "url": ("https://kaikki.org/viwiktionary/Ti%E1%BA%BFng%20Quan%20Tho%E1%BA%A1i/"
                     "kaikki.org-dictionary-Ti%E1%BA%BFngQuanTho%E1%BA%A1i.jsonl"),
             "path": SOURCES / "kaikki-zh-cmn.jsonl"},
            {"key": "kaikki-zh-vi", "gloss": "vi",
             "host": "vi.wiktionary.org", "section": "Tiếng Trung Quốc",
             "url": ("https://kaikki.org/viwiktionary/Ti%E1%BA%BFng%20Trung%20Qu%E1%BB%91c/"
                     "kaikki.org-dictionary-Ti%E1%BA%BFngTrungQu%E1%BB%91c.jsonl"),
             "path": SOURCES / "kaikki-zh-vi.jsonl"},
            {"key": "kaikki-zh-en", "gloss": "en",
             "host": "en.wiktionary.org", "section": "Chinese",
             "url": ("https://kaikki.org/dictionary/Chinese/"
                     "kaikki.org-dictionary-Chinese.jsonl"),
             "path": SOURCES / "kaikki-zh-en.jsonl",
             "slim": "morph_zh"},
        ],
        # Les lectures Hán Việt : la section vietnamienne du Wiktionnaire
        # anglais, la même que Việt–Pháp.
        "extra_sources": [VIETNAMESE_EN],
        "rescue": False,
        "morphology": "morph_zh",
        "credits": [
            "Wiktionnaire vietnamien (vi.wiktionary.org), extrait par "
            "wiktextract / kaikki.org — CC BY-SA 4.0",
            "Wiktionary anglais (en.wiktionary.org), extrait par "
            "wiktextract / kaikki.org — CC BY-SA 4.0",
            "FrequencyWords, Hermit Dave, d'après OpenSubtitles — CC BY-SA 4.0",
            "OpenCC, BYVoid et contributeurs (table traditionnel → simplifié) "
            "— Apache 2.0",
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


# --- vietnamien ---------------------------------------------------------------

# Les sous-titres encore, comme SUBTLEX pour l'anglais. Le fichier compte des
# syllabes, pas des mots : le vietnamien s'écrit syllabe par syllabe, et le
# corpus coupe aux espaces. morph_vi en tire un rang pour les mots composés.
FREQ_VI = SOURCES / "frequence-vi.txt"
FREQ_VI_URL = ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
               "master/content/2018/vi/vi_full.txt")


# --- chinois ------------------------------------------------------------------

# Les sous-titres encore, en chinois simplifié et déjà segmentés en mots.
FREQ_ZH = SOURCES / "frequence-zh.txt"
FREQ_ZH_URL = ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
               "master/content/2018/zh_cn/zh_cn_full.txt")

# Traditionnel -> simplifié, caractère par caractère. Sert à choisir la
# vedette affichée parmi les graphies que le Wiktionnaire relie déjà ; elle
# ne fabrique aucun mot. Épinglée sur un commit : la table bouge peu, mais
# un changement silencieux changerait des vedettes.
OPENCC_TS = SOURCES / "opencc-ts.txt"
OPENCC_TS_URL = ("https://raw.githubusercontent.com/BYVoid/OpenCC/"
                 "fae2a0a911c30764e669a7d8b0591cd8e852934a/data/dictionary/"
                 "TSCharacters.txt")


def kaikki_sources(code):
    """Les dumps kaikki d'une langue, dans l'ordre où leurs sens s'affichent.

    Pháp–Việt et Anh–Việt en ont un, tiré du Wiktionnaire vietnamien.
    Việt–Pháp en a deux. La forme est la même pour tous, et le pipeline ne
    connaît qu'elle.
    """
    cfg = lang(code)
    if "kaikki_sources" in cfg:
        return cfg["kaikki_sources"]
    section = "Tiếng Pháp" if code == "fr" else "Tiếng Anh"
    return [{"key": f"kaikki-{code}", "gloss": "vi",
             "host": "vi.wiktionary.org", "section": section,
             "url": cfg["kaikki_url"], "path": cfg["kaikki"]}]


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
