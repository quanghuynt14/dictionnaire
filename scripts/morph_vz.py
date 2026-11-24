#!/usr/bin/env python3
"""Việt–Trung : la morphologie du vietnamien, des étiquettes en vietnamien.

Tout vient de morph_vi — clé sans accents, ton déplacé, fréquence. Deux
différences seulement :

  - les étiquettes des sens [EN] sont en vietnamien, comme les entrées de
    Claude (« Danh từ », pas « Nom ») : le lecteur de Reindoo Hán est
    vietnamien ;
  - on ne garde du Wiktionnaire que les vedettes qui ont une entrée dans
    data/han-vz.jsonl. Le dictionnaire, ce sont ces entrées ; le Wiktionnaire
    ne fait que compléter. Le filtre sert aussi la mémoire : 83 Mo de JSON
    entier, sans lui, dans une machine déjà pleine.
"""

import json

import morph_vi
import sources as S
from morph_vi import (build, fold, frequency, keep_sense, merge,  # noqa: F401
                      redirects)

LABELS = {
    "noun": "Danh từ", "verb": "Động từ", "adj": "Tính từ", "adv": "Phó từ",
    "name": "Danh từ riêng", "pron": "Đại từ", "prep": "Giới từ",
    "conj": "Liên từ", "intj": "Thán từ", "particle": "Trợ từ",
    "classifier": "Loại từ", "num": "Số từ", "phrase": "Cụm từ",
    "prep_phrase": "Cụm từ", "proverb": "Tục ngữ", "idiom": "Thành ngữ",
    "onomatopoeia": "Từ tượng thanh", "combining_form": "Yếu tố cấu tạo từ",
    "suffix": "Hậu tố", "prefix": "Tiền tố", "det": "Từ hạn định",
    "postp": "Hậu giới từ", "contraction": "Từ rút gọn", "article": "Mạo từ",
}

_OWN = None


def own_words():
    global _OWN
    if _OWN is None:
        path = S.own_path("vz")
        _OWN = set()
        if path.exists():
            _OWN = {json.loads(l)["word"] for l in open(path, encoding="utf-8") if l.strip()}
    return _OWN


def keep(row):
    return morph_vi.keep(row) and row.get("word") in own_words()


def label(row):
    return LABELS.get(row.get("pos"))
