#!/usr/bin/env python3
"""La troisième langue : des sens en anglais pour Pháp–Việt, en français pour
Anh–Việt.

Huy apprend les trois langues ensemble. Un mot cherché doit donc montrer ses
deux autres langues, et chacune vient d'un wiki où quelqu'un l'a écrite :

  - « maison » : vi.wiktionary (vietnamien), puis en.wiktionary, section
    French (anglais) ;
  - « house » : vi.wiktionary (vietnamien), puis fr.wiktionary, section
    Anglais (français).

On ne passe jamais par le vietnamien pour relier le français à l'anglais.
Une traduction de traduction dérive, et personne ne peut la corriger sur
un wiki.

Ces sources **complètent** une vedette, elles n'en créent pas (`attach` dans
sources.py) : le dictionnaire reste vers le vietnamien, et un mot que le
Wiktionnaire vietnamien ignore n'entre pas par la porte anglaise.

`slim` est appelée par fetch.py pendant le téléchargement. Le dump anglais
du français pèse 593 Mo, le français de l'anglais 202 Mo : ni l'un ni
l'autre ne touche le disque en entier.
"""

# Les étiquettes du Wiktionnaire vietnamien, pour que les blocs anglais et
# français se rangent sous les mêmes titres que les vietnamiens. Une
# étiquette, pas un sens : on la traduit, on n'invente rien.
POS_VI = {
    "noun": "Danh từ", "verb": "Động từ", "adj": "Tính từ", "adv": "Phó từ",
    "pron": "Đại từ", "prep": "Giới từ", "conj": "Liên từ", "intj": "Thán từ",
    "det": "Từ hạn định", "article": "Mạo từ", "num": "Số từ",
    "name": "Danh từ riêng", "prefix": "Tiền tố", "suffix": "Hậu tố",
    "phrase": "Cụm từ", "abbrev": "Từ viết tắt", "contraction": "Từ rút gọn",
    "particle": "Tiểu từ",
}

# Pas des mots : des lettres, des symboles, des morceaux de proverbe.
SKIP_POS = {"character", "symbol", "punct", "proverb", "romanization"}

MAX_EXAMPLES = 3


def is_reference(sense):
    """« plural of maison », « Pluriel de chat » : un renvoi, pas un sens.

    La morphologie mène déjà de la forme au lemme, et le lemme a ses sens.
    """
    tags = set(sense.get("tags") or [])
    return bool(sense.get("form_of") or sense.get("alt_of")
                or tags & {"form-of", "alt-of"})


def slim(row):
    """Une ligne du dump -> ce que normalize en lit, ou None."""
    word = (row.get("word") or "").strip()
    pos = row.get("pos") or ""
    if not word or pos in SKIP_POS:
        return None
    senses = []
    for sense in row.get("senses") or []:
        glosses = [g for g in sense.get("glosses") or [] if g and g.strip()]
        if not glosses or is_reference(sense):
            continue
        item = {"glosses": glosses}
        tags = [t for t in sense.get("tags") or [] if t != "no-gloss"]
        if tags:
            item["tags"] = tags
        examples = []
        for ex in sense.get("examples") or []:
            text = (ex.get("text") or "").strip()
            if not text:
                continue
            # en.wiktionary a longtemps appelé la traduction « english ».
            tr = ex.get("translation") or ex.get("english")
            examples.append({"text": text, **({"translation": tr} if tr else {})})
            if len(examples) == MAX_EXAMPLES:
                break
        if examples:
            item["examples"] = examples
        senses.append(item)
    if not senses:
        return None
    return {"word": word, "lang": row.get("lang"), "pos": pos,
            "pos_title": POS_VI.get(pos), "senses": senses}
