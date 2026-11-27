#!/usr/bin/env python3
"""Vietnamien : pas de flexion, mais deux façons de taper un mot.

Le vietnamien ne conjugue ni n'accorde. Ce module ne rattache donc pas des
formes à un lemme comme morph_fr et morph_en ; il rattache ce qu'on **tape** à
ce qui est **écrit**. Deux cas, mesurés sur les deux dumps :

  1. **Sans accents.** Beaucoup tapent « an » pour « ăn », faute de clavier
     vietnamien. La clé repliée — sans diacritique, « đ » devenu « d », en
     minuscules — mène à tous les mots qu'elle peut vouloir dire : « an »
     donne ăn, ân, ấn, án, an. La page de forme ambiguë les montre tous ; le
     rang les ordonne.

  2. **Le ton sur l'autre voyelle.** « hoà » et « hòa », « thuý » et « thúy » :
     deux orthographes en usage, et les deux Wiktionnaires ne choisissent pas
     la même pour tous les mots. On indexe l'autre place du ton, pour que les
     deux mènent à la même page.

Ce que le module ne fait pas : deviner la frontière des mots. « tham nhũng »
est une vedette parce que le Wiktionnaire l'écrit ; une phrase collée n'est
pas découpée.
"""

import re
import unicodedata

import sources as S

# Les cinq marques de ton, en forme décomposée. Les autres diacritiques —
# brève, circonflexe, corne — font partie de la voyelle et restent en place.
TONES = {"̀", "́", "̃", "̉", "̣"}

# Les paires où la place du ton varie d'un auteur à l'autre, quand elles
# finissent la syllabe : « hoà/hòa », « khoẻ/khỏe », « thuý/thúy ». Suivies
# d'une consonne (« hoàn »), la place est fixée et ne varie pas.
MOVABLE = ("oa", "oe", "uy")

# Les catégories qu'on écarte. Les sinogrammes et les lectures romanisées
# décrivent l'écriture chinoise, pas un mot qu'on lit dans un texte en
# quốc ngữ — et un lecteur francophone n'a pas de clavier pour les chercher.
SKIP_POS = {"character", "romanization"}

# L'étiquette affichée devant chaque sens. Le Wiktionnaire français en donne
# une (« Nom commun 2 ») ; l'anglais n'en donne pas, d'où la table.
LABELS = {
    "noun": "Nom", "verb": "Verbe", "adj": "Adjectif", "adv": "Adverbe",
    "name": "Nom propre", "pron": "Pronom", "prep": "Préposition",
    "conj": "Conjonction", "intj": "Interjection", "particle": "Particule",
    "classifier": "Classificateur", "num": "Numéral", "phrase": "Locution",
    "prep_phrase": "Locution", "proverb": "Proverbe", "idiom": "Expression",
    "onomatopoeia": "Onomatopée", "combining_form": "Élément",
    "suffix": "Suffixe", "prefix": "Préfixe", "det": "Déterminant",
    "postp": "Postposition", "contraction": "Contraction",
}


def fold(text):
    """« Đẹp » -> « dep ». Ce qu'on tape sans clavier vietnamien."""
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.combining(ch):
            continue
        out.append({"đ": "d", "Đ": "D"}.get(ch, ch))
    return "".join(out).lower()


def keep(row):
    """La ligne kaikki décrit-elle un mot en quốc ngữ ?"""
    if row.get("pos") in SKIP_POS:
        return False
    word = row.get("word") or ""
    return any("a" <= c <= "z" for c in fold(word))


# Les renvois que wiktextract ne marque pas comme tels : 399 sens du
# Wiktionnaire anglais, sans clé alt_of, dont la glose entière est
# « Traditional tone placement spelling of hoà. ».
TONE_REFERENCE = re.compile(r"^(?:Traditional|Modern) tone placement spelling of (.+?)\.?$")


def reference_of(sense):
    """Les mots vers lesquels un sens ne fait que renvoyer."""
    targets = [ref.get("word") for ref in
               (sense.get("alt_of") or []) + (sense.get("form_of") or [])]
    for gloss in sense.get("glosses", []):
        match = TONE_REFERENCE.match(gloss.strip())
        if match:
            targets.append(match.group(1))
    return [t.strip() for t in targets if t and t.strip()]


def keep_sense(sense):
    """Un renvoi d'orthographe n'est pas un sens, une liste de locutions non plus.

    Le Wiktionnaire anglais a 3 245 renvois marqués — « alternative spelling
    of Thuý » — et 399 qui ne le sont pas. La clé repliée et `redirects`
    mènent déjà au mot visé ; afficher la phrase n'apprendrait rien de plus,
    et en anglais.

    Le Wiktionnaire français range parfois une liste de locutions sous une
    définition, et wiktextract la prend pour une glose : « ăn » avait pour sens
    « * cha ăn mặn, con khát nước ». 25 cas. Ce n'est pas un sens du mot.
    """
    if reference_of(sense):
        return False
    glosses = [g.strip() for g in sense.get("glosses", []) if g.strip()]
    return not glosses or not all(g.startswith("*") for g in glosses)


def label(row):
    """L'étiquette française d'un bloc, sans le numéro du Wiktionnaire."""
    title = (row.get("pos_title") or "").rstrip("0123456789 ")
    return title or LABELS.get(row.get("pos"), None)


def move_tone(syllable):
    """L'autre place du ton dans une syllabe, ou None s'il n'y en a pas."""
    parts = list(unicodedata.normalize("NFD", syllable))
    tones = [c for c in parts if c in TONES]
    if len(tones) != 1:
        return None
    base = unicodedata.normalize("NFC", "".join(c for c in parts if c not in TONES))
    low = base.lower()
    if not low.endswith(MOVABLE) or len(low) < 2:
        return None
    # « quý » : le u appartient au « qu », le ton ne peut aller que sur le y.
    if low[:-2].endswith("q"):
        return None
    first, second = len(base) - 2, len(base) - 1
    current = unicodedata.normalize("NFD", syllable)
    # Où est le ton aujourd'hui ? Sur la voyelle qui le précède dans la forme
    # décomposée.
    position = None
    index = -1
    for c in current:
        if c in TONES:
            position = index
        elif not unicodedata.combining(c):
            index += 1
    target = second if position == first else first
    out = []
    for i, c in enumerate(base):
        out.append(c)
        if i == target:
            out.append(tones[0])
    return unicodedata.normalize("NFC", "".join(out))


def other_spelling(word):
    """« hoà bình » -> « hòa bình ». None si le mot n'a qu'une orthographe."""
    changed = False
    out = []
    for syllable in word.split(" "):
        moved = move_tone(syllable)
        if moved and moved != syllable:
            changed = True
            out.append(moved)
        else:
            out.append(syllable)
    return " ".join(out) if changed else None


class Rank:
    """mot -> rang, à partir d'une fréquence de syllabes.

    Le corpus compte les syllabes. Un mot d'une syllabe prend sa fréquence ;
    un mot composé, celle de sa syllabe la plus rare, divisée par dix pour
    chaque syllabe en plus. C'est une approximation, et elle le reste : elle
    ne sait pas que « ăn uống » est courant et « ăn mày » moins. Elle suffit à
    ce qu'on lui demande — mettre « ăn » avant « ẳn » quand on tape « an », et
    faire passer les mots courts et fréquents en tête de la coupe.
    """

    def __init__(self, counts):
        self.counts = counts

    def __len__(self):
        return len(self.counts)

    def get(self, word, default=0.0):
        syllables = word.lower().split()
        if not syllables:
            return default
        counts = [self.counts.get(s, 0.0) for s in syllables]
        value = min(counts) / (10 ** (len(syllables) - 1))
        # Le corpus est en minuscules : « Người » (un nom propre) et
        # « người » y ont le même compte. Taper « nguoi » veut dire le second.
        # Diviser par deux ne suffisait pas : le nom de famille « Lại » et le
        # prénom « Được » restaient dans les 300 premiers mots, devant
        # « bác » ou « thương ». Un nom propre n'a pas la fréquence du mot
        # commun qu'il écrit ; un centième l'en approche mieux.
        if word[:1].isupper():
            value /= 100
        return value or default


def frequency():
    counts = {}
    if not S.FREQ_VI.exists():
        return Rank(counts)
    for line in open(S.FREQ_VI, encoding="utf-8", errors="replace"):
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            counts[parts[0].lower()] = float(parts[1])
        except ValueError:
            continue
    return Rank(counts)


GLOSS_ORDER = {"fr": 0, "en": 1}


def merge(by_word, freq):
    """Une page par mot, quelle que soit la place du ton.

    Les deux Wiktionnaires ne placent pas le ton au même endroit : l'un a
    « thuỷ », l'autre « thủy », et sans fusion le lecteur trouve deux pages
    pour un mot — 485 vedettes fusionnées, mesuré le 2026-11-20. On garde l'orthographe la
    plus fréquente dans les sous-titres ; l'autre passe dans l'index des
    formes, par `build`, et mène à la même page.

    Un bloc de la variante qui répète mot pour mot un bloc gardé — même wiki,
    même catégorie, mêmes gloses — est écarté : c'est la même définition,
    écrite deux fois sur le wiki.
    """
    for word in sorted(by_word):
        other = other_spelling(word)
        if word not in by_word or not other or other not in by_word:
            continue
        keep, drop = sorted((word, other), key=lambda w: (-freq.get(w), w))
        seen = {signature(r) for r in by_word[keep]}
        rows = by_word[keep] + [r for r in by_word.pop(drop) if signature(r) not in seen]
        rows.sort(key=lambda r: GLOSS_ORDER.get((r.get("_src") or {}).get("gloss"), 2))
        by_word[keep] = rows
    return by_word


def signature(row):
    glosses = tuple(g for s in row.get("senses", []) for g in s.get("glosses", []))
    return ((row.get("_src") or {}).get("gloss"), row.get("pos"), glosses)


def build(entries_by_head):
    """(forme tapée, vedette, analyse) pour chaque vedette gardée.

    Sous une clé repliée, les vedettes sortent par fréquence : « an » montre
    « ăn » avant « ẩn ».
    """
    rank = frequency()
    out = []
    folded = respelled = 0
    for word in entries_by_head:
        key = fold(word)
        if key != word:
            out.append((key, word, "không dấu"))
            folded += 1
        other = other_spelling(word)
        if other:
            out.append((other, word, "dấu đặt chỗ khác"))
            respelled += 1
    out.sort(key=lambda t: (t[0], -rank.get(t[1]), t[1]))
    return out, f"{folded:,} clés sans accents, {respelled:,} tons déplacés"


def redirects(by_word):
    """(variante, mot visé, analyse) pour les renvois qu'on n'affiche pas.

    keep_sense écarte la phrase « alternative form of suyễn ». Le lien, lui,
    reste utile : chercher « siễn » doit mener à « suyễn ». Il passe donc par
    l'index des formes, comme « went » mène à « go ».
    """
    out = []
    for word, rows in by_word.items():
        for row in rows:
            for sense in row.get("senses", []):
                for target in reference_of(sense):
                    if target != word:
                        out.append((word, target, "cách viết khác"))
    return out
