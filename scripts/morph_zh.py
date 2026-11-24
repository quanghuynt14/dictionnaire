#!/usr/bin/env python3
"""Chinois : pas de flexion, mais quatre façons de taper un mot.

Comme morph_vi, ce module rattache ce qu'on **tape** à ce qui est **écrit** :

  1. **L'autre écriture.** « 學 » et « 学 », « 中國 » et « 中国 ». Le
     Wiktionnaire les relie déjà (une page simplifiée renvoie à la page
     traditionnelle) ; on en fait une seule entrée, sous la forme simplifiée,
     celle du continent et des manuels.

  2. **Le pinyin**, avec ou sans tons, collé ou en syllabes, et avec les tons
     en chiffres : « zhōngguó », « zhongguo », « zhong guo », « zhong1guo2 ».

Il décide aussi ce qu'on garde du chinois : le mandarin. Le Wiktionnaire
anglais décrit aussi le cantonais, le hokkien, le wu… Un sens marqué d'un
de ces parlers, sans le mandarin, ne sert pas à un apprenant du mandarin.

Et il ajoute ce qu'un Vietnamien veut savoir d'un sinogramme : sa lecture
Hán Việt, lue dans la section vietnamienne du Wiktionnaire anglais.
"""

import collections
import json
import re
import unicodedata

import sources as S

# --- écriture -----------------------------------------------------------------


def is_han(ch):
    o = ord(ch)
    return (0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF
            or 0x20000 <= o <= 0x3134F or ch == "〇")


def has_han(word):
    return any(is_han(c) for c in word or "")


_TS = None


def ts_table():
    """Traditionnel -> simplifié, caractère par caractère (OpenCC)."""
    global _TS
    if _TS is None:
        _TS = {}
        if S.OPENCC_TS.exists():
            for line in open(S.OPENCC_TS, encoding="utf-8"):
                if line.startswith("#") or "\t" not in line:
                    continue
                key, values = line.rstrip("\n").split("\t", 1)
                _TS[key] = values.split()
    return _TS


def _options(ch):
    return ts_table().get(ch, [ch])


def also_simplified(word):
    """Une graphie qui s'écrit aussi en simplifié : 著 (zhù), 乾 (qián), 了.
    « 聽 » ou « 後 » n'en sont pas : le simplifié écrit 听, 后."""
    return all(c in _options(c) for c in word)


def simplifies_to(trad, simp):
    """OpenCC admet-il `simp` comme forme simplifiée de `trad` ?"""
    return (trad != simp and len(trad) == len(simp)
            and all(s in _options(t) for t, s in zip(trad, simp)))


def simplify(word, strict=False):
    """La graphie simplifiée, ou None si `strict` et qu'un caractère hésite."""
    table = ts_table()
    out = []
    for ch in word:
        options = table.get(ch, [ch])
        if strict and len(options) > 1:
            return None
        out.append(options[0])
    return "".join(out)


# --- ce qu'on garde -----------------------------------------------------------

# Les parlers qui ne sont pas le mandarin. Un sens qui porte l'un d'eux, et
# pas « Mandarin », est écarté.
TOPOLECTS = {
    "Cantonese", "Hokkien", "Hakka", "Min", "Wu", "Teochew", "Xiang", "Gan",
    "Jin", "Shanghainese", "Hainanese", "Min-Nan", "Min-Dong", "Min-Bei",
    "Puxian-Min", "Taiwanese-Hokkien", "Zhangzhou-Hokkien", "Xiamen",
    "Quanzhou", "Taishanese", "Southern-Pinghua", "Leizhou", "Guangzhou-Cantonese",
    "Hong-Kong-Cantonese", "Philippine-Hokkien", "Singaporean-Hokkien",
    "Penang-Hokkien", "Medan-Hokkien", "Suzhounese", "Wenzhounese", "Fuzhou",
    "Jyutping", "POJ", "Peng'im", "Wugniu", "Phak-fa-su", "Sino-Korean",
}

# Les prononciations du mandarin standard. Chengdu, Xi'an, Nankin sont du
# mandarin aussi, mais pas celui qu'on apprend.
STANDARD = {"Mandarin", "Pinyin", "Standard", "Standard-Chinese",
            "Mainland-China", "standard"}

# L'étiquette affichée devant chaque sens, quand le wiki n'en donne pas en
# vietnamien.
LABELS = {
    "noun": "Danh từ", "verb": "Động từ", "adj": "Tính từ", "adv": "Phó từ",
    "name": "Danh từ riêng", "pron": "Đại từ", "prep": "Giới từ",
    "conj": "Liên từ", "intj": "Thán từ", "particle": "Trợ từ",
    "classifier": "Lượng từ", "num": "Số từ", "phrase": "Cụm từ",
    "proverb": "Tục ngữ", "idiom": "Thành ngữ", "character": "Chữ Hán",
    "suffix": "Hậu tố", "prefix": "Tiền tố", "det": "Từ hạn định",
    "postp": "Hậu giới từ", "onomatopoeia": "Từ tượng thanh",
    "abbrev": "Từ viết tắt", "affix": "Phụ tố", "infix": "Trung tố",
    "contraction": "Từ rút gọn", "punct": "Dấu câu", "symbol": "Ký hiệu",
}

# Les pos_title vietnamiens qui ne disent rien de la catégorie.
VAGUE_TITLES = {"Định nghĩa", "Latinh hóa"}


def dialectal(tags):
    """Un sens propre à un autre parler. « Taiwanese-Mandarin » est du
    mandarin : kaikki le colle, avec « Jin », à tous les sens de 著, et les
    perdre ôtait à 著 (et à 着) zhe et zhù."""
    tags = set(tags or [])
    return bool(tags & TOPOLECTS) and not any(t.endswith("Mandarin") for t in tags)


REFERENCE = re.compile(
    r"^(?:Bính âm Hán ngữ của|(?:alternative|simplified|traditional|variant|"
    r"obsolete|archaic|dated|nonstandard|ancient) (?:form|spelling) of)\s",
    re.I)


def reference_of(sense):
    """Les mots vers lesquels un sens ne fait que renvoyer."""
    targets = [ref.get("word") for ref in
               (sense.get("alt_of") or []) + (sense.get("form_of") or [])]
    targets = [t.strip() for t in targets if t and has_han(t)]
    if not targets:
        for gloss in sense.get("glosses") or []:
            if REFERENCE.match(gloss.strip()):
                targets += [w for w in re.findall(r"[^\s(（,，;；]+", gloss) if has_han(w)][:1]
    return targets


def keep(row):
    """Une vedette en sinogrammes, ou une ligne de pinyin à rattacher."""
    if row.get("pos") == "romanization":
        return True
    return has_han(row.get("word"))


def keep_sense(sense):
    """Ni renvoi, ni sens propre à un autre parler que le mandarin."""
    if reference_of(sense):
        return False
    return not dialectal(sense.get("tags"))


def label(row):
    src = row.get("_src") or {}
    title = (row.get("pos_title") or "").rstrip("0123456789 ")
    if src.get("gloss") == "vi" and title and title not in VAGUE_TITLES:
        base = title
    else:
        base = LABELS.get(row.get("pos"))
    # Une vedette simplifiée qui réunit plusieurs pages (voir absorb) : on
    # dit de quelle graphie traditionnelle vient chaque sens, et lesquels
    # sont ceux du caractère simplifié lui-même.
    if row.get("_trad"):
        return f"{base} – {row['_trad']}" if base else row["_trad"]
    if row.get("_own"):
        mark = f"nghĩa riêng của {row['_own']}"
        return f"{base} – {mark}" if base else mark
    return base


# Les classificateurs du Wiktionnaire anglais disent pour quel parler ils
# valent : « horse (Classifier: 匹 m c; 隻／只 m c h mn) ». On garde ceux du
# mandarin (m) et on retire les codes.
CLASSIFIER = re.compile(r"\s*\(Classifier: ([^)]*)\)")


def _classifiers(match):
    kept = []
    for item in match.group(1).split(";"):
        parts = item.split()
        if len(parts) >= 2 and "m" in parts[1:]:
            kept.append(parts[0])
    return f" (Lượng từ: {'; '.join(kept)})" if kept else ""


def gloss(text):
    return CLASSIFIER.sub(_classifiers, text).strip()


def examples(sense):
    """Les exemples du mandarin, une fois : le wiki écrit chacun deux fois,
    en traditionnel puis en simplifié. On garde le simplifié."""
    chosen = {}
    for ex in sense.get("examples") or []:
        text = (ex.get("text") or "").strip()
        tags = set(ex.get("tags") or [])
        if not text or tags & TOPOLECTS:
            continue
        roman = (ex.get("roman") or "").strip()
        tr = (ex.get("translation") or ex.get("english") or "").strip()
        key = (roman, tr) if (roman or tr) else (text, "")
        if key in chosen and "Simplified-Chinese" not in tags:
            continue
        item = {"src": text, "tr": tr or None}
        if roman:
            item["roman"] = roman
        chosen[key] = item
    return list(chosen.values())


# --- le filtre du dump anglais -------------------------------------------------


def _words(items, limit):
    out = []
    for it in items or []:
        w = it.get("word") if isinstance(it, dict) else None
        if w and has_han(w) and not dialectal(it.get("tags")) and w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return [{"word": w} for w in out]


def slim(row):
    """Une ligne du dump anglais -> ce que ce module en lit, ou None.

    Appelée par fetch.py pendant le téléchargement : le dump entier ne
    touche jamais le disque.
    """
    word = row.get("word") or ""
    if not has_han(word):
        return None
    if row.get("redirects") and not any(s.get("glosses") for s in row.get("senses") or []):
        return {"word": word, "pos": row.get("pos"), "redirects": row["redirects"]}
    sounds = []
    for s in row.get("sounds") or []:
        tags = s.get("tags") or []
        if "Mandarin" not in tags:
            continue
        if "Pinyin" in tags and s.get("zh_pron"):
            sounds.append({"zh_pron": s["zh_pron"], "tags": tags})
        elif s.get("mp3_url"):
            sounds.append({"mp3_url": s["mp3_url"], "tags": tags})
    if not any("zh_pron" in s for s in sounds):
        return None
    senses = []
    for sense in row.get("senses") or []:
        if not sense.get("glosses") or dialectal(sense.get("tags")):
            continue
        item = {"glosses": sense["glosses"]}
        for k in ("tags", "alt_of", "form_of"):
            if sense.get(k):
                item[k] = sense[k]
        exs = [{k: e[k] for k in ("text", "roman", "translation", "tags") if e.get(k)}
               for e in sense.get("examples") or []
               if e.get("text") and not set(e.get("tags") or []) & TOPOLECTS]
        if exs:
            item["examples"] = exs[:8]
        senses.append(item)
    if not senses:
        return None
    out = {"word": word, "pos": row.get("pos"), "senses": senses, "sounds": sounds}
    # « 并 » a ses propres sens (bīng) *et* renvoie à 並, 併 : le renvoi
    # tient sur la même ligne, et merge en a besoin.
    if row.get("redirects"):
        out["redirects"] = row["redirects"]
    forms = [f for f in row.get("forms") or []
             if set(f.get("tags") or []) & {"Simplified-Chinese", "Traditional-Chinese"}
             and "alternative" not in (f.get("tags") or [])]
    if forms:
        out["forms"] = [{"form": f["form"], "tags": f["tags"]} for f in forms]
    for key, limit in (("synonyms", 8), ("antonyms", 8), ("derived", 24)):
        words = _words(row.get(key), limit)
        if words:
            out[key] = words
    viet = [d["word"] for d in row.get("descendants") or []
            if d.get("lang_code") == "vi" and d.get("word")]
    if viet:
        out["descendants"] = [{"lang_code": "vi", "word": w} for w in viet[:4]]
    return out


# --- pinyin --------------------------------------------------------------------

# Les syllabes possibles, engendrées plutôt que recopiées. La liste déborde
# (« bü » n'existe pas) ; peu importe : elle ne sert qu'à couper, et le
# nombre de sinogrammes tranche entre deux coupes.
INITIALS = ["", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h", "j", "q",
            "x", "zh", "ch", "sh", "r", "z", "c", "s", "y", "w"]
FINALS = ["a", "o", "e", "i", "u", "ü", "ai", "ei", "ao", "ou", "an", "en", "ang",
          "eng", "ong", "er", "ia", "ie", "iao", "iu", "ian", "in", "iang", "ing",
          "iong", "ua", "uo", "uai", "ui", "uan", "un", "uang", "ue", "üe", "üan",
          "ün", "ueng"]
SYLLABLES = {i + f for i in INITIALS for f in FINALS} | {
    "r", "m", "n", "ng", "hm", "hng", "ê"}
LONGEST = max(map(len, SYLLABLES))

# Les marques de ton, en forme décomposée. Le tréma de « ü » n'en est pas une.
TONE_MARKS = {"̄": "1", "́": "2", "̌": "3", "̀": "4"}


def toneless(text):
    nfd = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if c not in TONE_MARKS))


def tone_of(syllable):
    for c in unicodedata.normalize("NFD", syllable):
        if c in TONE_MARKS:
            return TONE_MARKS[c]
    return "5"


def _cuts(chunk, limit=24):
    """Toutes les coupes d'un bloc sans séparateur, jusqu'à `limit`."""
    memo = {}

    def go(i):
        if i == len(chunk):
            return [[]]
        if i in memo:
            return memo[i]
        out = []
        for j in range(min(len(chunk), i + LONGEST), i, -1):
            if chunk[i:j] in SYLLABLES:
                for rest in go(j):
                    out.append([(i, j)] + rest)
                    if len(out) >= limit:
                        break
            if len(out) >= limit:
                break
        memo[i] = out
        return out

    return go(0)


def syllables(pinyin, count):
    """« Zhōngguó », 2 -> ["zhōng", "guó"]. None si la coupe échoue.

    `count` est le nombre de sinogrammes : il choisit entre « xi'an » et
    « xian » quand le wiki n'a pas mis d'apostrophe.
    """
    text = unicodedata.normalize("NFC", pinyin.lower())
    bare = toneless(text)
    if len(bare) != len(text):
        return None
    pieces = [(m.start(), m.end()) for m in re.finditer(r"[a-zü]+", bare)]
    combos = [[]]
    for start, end in pieces:
        cuts = _cuts(bare[start:end])
        if not cuts:
            return None
        combos = [c + [(start + a, start + b) for a, b in cut]
                  for c in combos for cut in cuts][:64]
    best = min(combos, key=lambda c: (abs(len(c) - count), len(c)))
    return [text[a:b] for a, b in best]


def clean_pinyin(text):
    """« mǎ (ma³) » -> « mǎ ». Le reste tel que le wiki l'écrit."""
    return re.sub(r"\s*\(.*?\)\s*$", "", text or "").strip()


def pinyin_forms(pinyin, count):
    """Ce qu'on tape pour un pinyin : avec ou sans tons, collé ou non,
    et les tons en chiffres."""
    sylls = syllables(pinyin, count)
    if not sylls:
        return set()
    bare = [toneless(s) for s in sylls]
    forms = {"".join(sylls), " ".join(sylls), "".join(bare), " ".join(bare),
             "".join(b + tone_of(s) for b, s in zip(bare, sylls))}
    # Sans clavier pinyin, « ü » se tape « v » (la convention des claviers
    # chinois) ou « u ».
    for f in list(forms):
        if "ü" in f:
            forms.add(f.replace("ü", "v"))
            forms.add(f.replace("ü", "u"))
    return {f for f in forms if f}


# --- Hán Việt ------------------------------------------------------------------

SINO_VIET = re.compile(r"Sino-Vietnamese word from ([^\s,.;(“\"]+)")
_HV = None


def _add(table, key, reading):
    reading = (reading or "").strip()
    if key and reading and reading.lower() not in (r.lower() for r in table[key]):
        table[key].append(reading)


def _fits(hanzi, reading):
    """Une syllabe par sinogramme : « hảo hạng » n'est pas la lecture de 好,
    même si son étymologie commence par lui."""
    hanzi, reading = hanzi or "", reading or ""
    return (bool(hanzi) and all(is_han(c) for c in hanzi) and not has_han(reading)
            and len(reading.split()) == len(hanzi))


def hanviet_tables():
    """(caractère -> lectures, mot -> lectures), depuis le Wiktionnaire anglais.

    Trois indices, du plus sûr au moins sûr : la page vietnamienne d'un mot
    dit « Sino-Vietnamese word from 學生 » ; la page d'un caractère liste ses
    composés avec leur lecture (學生 → học sinh) ; et elle donne la lecture
    du caractère seul (« han-viet-reading »).
    """
    global _HV
    if _HV is not None:
        return _HV
    chars, words = collections.defaultdict(list), collections.defaultdict(list)
    path = S.VIETNAMESE_EN["path"]
    if path.exists():
        for line in open(path, encoding="utf-8"):
            if "han-viet-reading" not in line and "Sino-Vietnamese word from" not in line:
                continue
            row = json.loads(line)
            word = row.get("word") or ""
            match = SINO_VIET.search(row.get("etymology_text") or "")
            if match and _fits(match.group(1), word):
                _add(words, match.group(1), word)
            if row.get("pos") != "character":
                continue
            related = list(row.get("related") or [])
            for sense in row.get("senses") or []:
                related += sense.get("related") or []
            for rel in related:
                if "han-viet-reading" in (rel.get("tags") or []):
                    _add(chars, word, rel.get("word"))
            for d in row.get("derived") or []:
                roman = (d.get("roman") or "").split("/")[0]
                if _fits(d.get("word"), roman):
                    _add(words, d["word"], roman)
    _HV = (chars, words)
    return _HV


def hanviet(forms):
    """Les lectures Hán Việt d'une vedette, sous l'une de ses graphies.

    Un mot sans lecture notée se compose caractère par caractère, mais
    seulement si chaque caractère n'en a qu'une : « 行 » se lit hành ou
    hàng, et deviner serait se tromper une fois sur deux.
    """
    chars, words = hanviet_tables()
    # Le caractère seul d'abord : « minh », pas « Minh », la dynastie.
    found = collections.defaultdict(list)
    for form in forms:
        if len(form) == 1:
            for r in chars.get(form, []):
                _add(found, "x", r)
    for form in forms:
        for r in words.get(form, []):
            _add(found, "x", r)
    out = found["x"]
    if out:
        return out[:4]
    for form in forms:
        if len(form) < 2 or not all(is_han(c) for c in form):
            continue
        readings = [chars.get(c, []) for c in form]
        if all(len(r) == 1 for r in readings):
            return [" ".join(r[0].lower() for r in readings)]
    return []


# --- fréquence -----------------------------------------------------------------


class Rank:
    """mot -> rang, depuis les sous-titres (simplifié, déjà segmenté).

    Un mot absent du corpus mais glosé en vietnamien passe devant un mot
    absent que seul l'anglais connaît : `boost` le dit.
    """

    def __init__(self, counts):
        self.counts = counts
        self.boost = {}

    def __len__(self):
        return len(self.counts)

    def get(self, word, default=0.0):
        value = self.counts.get(word)
        if value is None:
            value = self.counts.get(simplify(word), 0.0)
        return (value + self.boost.get(word, 0.0)) or default


_RANK = None


def frequency():
    global _RANK
    if _RANK is None:
        counts = {}
        if S.FREQ_ZH.exists():
            for line in open(S.FREQ_ZH, encoding="utf-8", errors="replace"):
                parts = line.split()
                if len(parts) == 2:
                    try:
                        counts.setdefault(parts[0], float(parts[1]))
                    except ValueError:
                        pass
        _RANK = Rank(counts)
    return _RANK


# --- une entrée par mot, quelle que soit l'écriture ------------------------------

# Rempli par merge, lu par extra, sounds, build et redirects.
GROUPS = {}
HEAD_OF = {}
REFERENCES = []

GLOSS_ORDER = {"vi": 0, "en": 1}


def has_body(rows):
    return any(keep_sense(s) and s.get("glosses")
               for r in rows for s in r.get("senses") or [])


def merge(by_word, freq):
    """Les graphies d'un même mot -> une entrée, sous la simplifiée.

    Trois liens, tous écrits par le wiki : la page simplifiée qui renvoie à
    la traditionnelle (voir absorb : « 发 » renvoie à 發 *et* à 髮, et
    réunit les deux, chacun groupé) ; la forme marquée Simplified-Chinese
    d'une page ; et, pour les mots de deux caractères ou plus, la conversion
    OpenCC quand elle est sans ambiguïté et que les deux pages existent.
    """
    GROUPS.clear()
    HEAD_OF.clear()
    REFERENCES.clear()

    # Les lignes de pinyin du Wiktionnaire vietnamien : « gà », bính âm de
    # 尬. Elles donnent une prononciation, pas une entrée.
    romanized = collections.defaultdict(list)
    for word in [w for w, rows in by_word.items() if not has_han(w)]:
        for row in by_word.pop(word):
            for sense in row.get("senses") or []:
                for t in reference_of(sense):
                    if word not in romanized[t]:
                        romanized[t].append(word)

    parent = {w: w for w in by_word}

    def find(w):
        while parent[w] != w:
            parent[w] = parent[parent[w]]
            w = parent[w]
        return w

    def union(a, b):
        if a in parent and b in parent:
            parent[find(a)] = find(b)

    # Les caractères traditionnels qu'OpenCC simplifie d'une seule façon :
    # « 達 » -> 达. Ils complètent les renvois que kaikki a perdus.
    only_simple = collections.defaultdict(list)
    for trad, options in ts_table().items():
        if len(options) == 1 and options[0] != trad:
            only_simple[options[0]].append(trad)

    ambiguous, absorbs, redirect_of = {}, {}, {}
    for word, rows in by_word.items():
        stub = not has_body(rows)
        targets = []
        for row in rows:
            for t in row.get("redirects") or []:
                if t != word and t in by_word and t not in targets:
                    targets.append(t)
            for f in row.get("forms") or []:
                if set(f.get("tags") or []) & {"Simplified-Chinese", "Traditional-Chinese"}:
                    union(f["form"], word)
        redirect_of[word] = targets
        if also_simplified(word):
            # Une graphie simplifiée qui renvoie à sa traditionnelle : « 听 »
            # -> 聽, « 发 » -> 發 et 髮. Elle prend leurs sens (absorb), même
            # quand elle a les siens : 听 est aussi un caractère rare (yǐn,
            # « sourire »), mais celui qu'on lit est 聽. « 学 » renvoie à 學
            # et à 孛 : seul le premier se simplifie en 学.
            confirmed = [t for t in targets if simplifies_to(t, word)]
            if not confirmed and stub and len(targets) == 1:
                # « 着 » -> 著, qu'OpenCC garde tel quel : 着 est le plus
                # courant, c'est lui qu'on écrit. « 㐀 » -> 丘 n'est qu'une
                # graphie rare de 丘 : une seule entrée, sous 丘.
                if freq.get(word) > freq.get(targets[0]):
                    confirmed = targets
                else:
                    union(word, targets[0])
            if len(word) == 1:
                # kaikki perd des renvois : « 达 » ne dit plus 達, « 台 » ne
                # garde que 檯 (pas 臺 ni 颱), « 几 » oublie 幾. OpenCC les
                # rend, quand il ne simplifie le traditionnel qu'en ce
                # caractère et que le traditionnel ne s'écrit pas aussi tel
                # quel en simplifié.
                confirmed += [t for t in only_simple.get(word, [])
                              if t in by_word and t not in confirmed
                              and has_body(by_word[t]) and not also_simplified(t)]
            if confirmed:
                absorbs[word] = confirmed
            rest = [t for t in targets if t not in confirmed]
            if rest and stub:
                ambiguous[word] = rest
        elif stub:
            # Une variante traditionnelle (« 竝 » -> 並) : une seule entrée.
            if len(targets) == 1:
                union(word, targets[0])
            elif len(targets) > 1:
                ambiguous[word] = targets
        if len(word) >= 2:
            simple = simplify(word, strict=True)
            if simple and simple != word:
                union(simple, word)

    groups = collections.defaultdict(list)
    for word in by_word:
        groups[find(word)].append(word)

    merged = {}
    for members in groups.values():
        bodies = [m for m in members if has_body(by_word[m])]
        if not bodies:
            continue
        # La page principale : celle qui a le plus de sens. Sa forme
        # simplifiée, si le groupe la contient, devient la vedette.
        main = max(bodies, key=lambda w: (len(by_word[w]), freq.get(w), w))
        head = simplify(main) if simplify(main) in members else main
        # OpenCC ne simplifie pas 藉口 en 借口 (藉 a deux sorties), ni 睡著
        # en 睡着 (il garde 著). La vedette : la plus fréquente des graphies
        # simplifiées du groupe, celles qu'OpenCC admet ou qui renvoient à
        # la page principale. Un renvoi seul ne suffit pas : « 囯 » renvoie
        # aussi à 國, mais personne ne l'écrit ; il doit être plus fréquent
        # que la page.
        picks = [m for m in members if also_simplified(m) and (
            m == main or simplifies_to(main, m)
            or (main in redirect_of.get(m, ()) and freq.get(m) > freq.get(main)))]
        if picks:
            head = max(picks, key=lambda m: (freq.get(m), m == head, m))
        rows, seen = [], set()
        for m in members:
            for row in by_word[m]:
                if not has_body([row]):
                    continue
                sig = ((row.get("_src") or {}).get("gloss"), row.get("pos"),
                       tuple(g for s in row.get("senses") or [] for g in s.get("glosses") or []))
                if sig in seen:
                    continue
                seen.add(sig)
                rows.append(dict(row, _page=m))
        rows.sort(key=lambda r: GLOSS_ORDER.get((r.get("_src") or {}).get("gloss"), 2))
        others = sorted((m for m in members if m != head), key=lambda m: (m != simplify(m), m))
        traditional = next((m for m in others if simplify(m) == head
                            or simplifies_to(m, head) or m in redirect_of.get(head, ())),
                           None)
        merged[head] = rows
        GROUPS[head] = {
            "variants": others,
            "traditional": traditional,
            "romanized": [p for m in members for p in romanized.get(m, [])],
        }
        for m in members:
            HEAD_OF[m] = head
        if any((r.get("_src") or {}).get("gloss") == "vi" for r in rows):
            freq.boost[head] = 0.5

    # Combien de mots s'écrivent avec chaque caractère : 聽 (聽說, 聽見…) en
    # a bien plus que 听 seul. absorb y lit lequel est le plus courant. On
    # ne compte que les pages anglaises qui ont des sens : le Wiktionnaire
    # anglais les met sous la graphie traditionnelle (听说 n'est qu'un
    # renvoi vers 聽說).
    compounds = collections.Counter(
        c for w, rows in by_word.items() if len(w) > 1
        and any((r.get("_src") or {}).get("gloss") == "en" and has_body([r]) for r in rows)
        for c in set(w))
    absorb(merged, absorbs, romanized, freq, compounds)

    # Les renvois : un mot dont un sens n'est que « alternative form of X »,
    # et les pages simplifiées à plusieurs cibles.
    for word, rows in by_word.items():
        for row in rows:
            for sense in row.get("senses") or []:
                for t in reference_of(sense):
                    REFERENCES.append((word, t, "dị thể"))
    for word, targets in ambiguous.items():
        for t in targets:
            REFERENCES.append((word, t, "giản thể"))
    return merged


def absorb(merged, absorbs, romanized, freq, compounds):
    """Une vedette simplifiée prend les sens de ses graphies traditionnelles.

    « 听 » est la forme simplifiée de 聽 (tīng, écouter), mais aussi un
    caractère à part (yǐn, sourire), avec sa propre page. Fondre les deux
    pages n'était permis qu'à une page sans sens ; 听 en a, et l'entrée
    n'affichait que yǐn, tandis que 聽 restait seul sous sa graphie
    traditionnelle. Ici, l'entrée 听 donne les sens et le pinyin de 聽, puis
    ceux de 听 seul, marqués comme tels. Plusieurs traditionnels (发 : 發,
    髮) se suivent, chacun groupé sous son caractère.

    L'ordre des groupes : le caractère qui entre dans le plus de mots
    d'abord. 聽 (聽說, 聽見…) passe devant 听 ; mais 只 (只是, 只有…) reste
    devant 隻, et 表 (表示, 代表…) devant 錶 : leurs sens à eux sont les
    courants.

    La page traditionnelle disparaît dans la simplifiée, sauf un caractère
    qu'on écrit aussi en simplifié : 著 (zhù) garde son entrée, et 着
    reprend ses sens. Un mot comme 睡著 n'est que l'autre graphie de 睡着.
    """
    heads = dict(HEAD_OF)
    members = collections.defaultdict(list)
    for m, h in heads.items():
        members[h].append(m)
    before = {h: list(rows) for h, rows in merged.items()}

    def weight(chars):
        return sum(compounds[c] for c in chars if len(c) == 1)

    for word in sorted(absorbs):
        hx = HEAD_OF.get(word)
        if hx is not None and hx != heads.get(word):
            continue                    # déjà fondu dans une autre entrée
        fresh = hx is None              # une page sans sens à elle : « 发 »
        if fresh:
            hx = word
        taken, seen = [], {hx}
        for t in absorbs[word]:
            ht = heads.get(t)
            if ht is None or ht in seen or HEAD_OF.get(t) == hx:
                continue
            seen.add(ht)
            taken.append((t, ht))
        if not taken:
            continue
        if fresh:
            HEAD_OF[word] = word
            GROUPS[word] = {"variants": [], "traditional": None,
                            "romanized": list(romanized.get(word, []))}
        # Le Wiktionnaire vietnamien décrit le caractère simplifié dans son
        # usage d'aujourd'hui (复 : lặp lại, khôi phục) : il reste en tête.
        # Les sens anglais de la page simplifiée sont ceux du caractère seul.
        own = merged.get(hx, [])
        own_vi = [r for r in own if (r.get("_src") or {}).get("gloss") == "vi"]
        own_en = [r for r in own if r not in own_vi]
        # (poids, rang, caractère, lignes). À poids égal : le traditionnel
        # pur, puis le caractère seul, puis celui qui s'écrit aussi en
        # simplifié (借 avant 藉, 干 avant 乾).
        parts = [(weight(members[ht]), 2 if also_simplified(t) else 0, t,
                  before.get(ht, [])) for t, ht in taken]
        if own_en:
            parts.append((weight([word]), 1, None, own_en))
        parts.sort(key=lambda p: (-p[0], p[1], -sum(len(r.get("senses") or [])
                                                    for r in p[3])))
        mark = len(parts) > 1
        rows, sigs = [], set()
        for _, _, t, part in [(0, 0, None, own_vi)] + parts:
            for r in part:
                sig = ((r.get("_src") or {}).get("gloss"), r.get("pos"),
                       tuple(g for s in r.get("senses") or [] for g in s.get("glosses") or []))
                if sig in sigs:
                    continue
                sigs.add(sig)
                if mark and part is not own_vi:
                    r = dict(r, _trad=t) if t else dict(r, _own=hx)
                rows.append(r)
        merged[hx] = rows
        # La graphie traditionnelle : celle du premier groupe traditionnel.
        taken = [(p[2], heads[p[2]]) for p in parts if p[2]]

        group = GROUPS[hx]
        group["traditional"] = taken[0][0]
        group["traditionals"] = [t for t, _ in taken]
        for t, ht in taken:
            other = GROUPS.get(ht, {})
            moved = [ht] + other.get("variants", [])
            if len(ht) == 1 and also_simplified(ht):
                moved = [t]                 # 著 garde son entrée ; 睡著 non
            else:
                merged.pop(ht, None)
                GROUPS.pop(ht, None)
                for m in members[ht]:
                    HEAD_OF[m] = hx
            for m in moved:
                if m != hx and m not in group["variants"]:
                    group["variants"].append(m)
            for p in other.get("romanized", []):
                if p not in group["romanized"]:
                    group["romanized"].append(p)
        if any((r.get("_src") or {}).get("gloss") == "vi" for r in rows):
            freq.boost[hx] = 0.5


# --- ce que l'entrée porte en plus ----------------------------------------------


def pinyin_of(rows, head=None):
    strict, loose = [], []
    for row in rows:
        for s in row.get("sounds") or []:
            tags = set(s.get("tags") or [])
            text = clean_pinyin(s.get("zh_pron"))
            if not text or "Mandarin" not in tags or "Pinyin" not in tags:
                continue
            target = strict if tags <= STANDARD and not s.get("raw_tags") else loose
            if text not in target:
                target.append(text)
    found = strict or loose
    if not found and head:
        found = list(GROUPS.get(head, {}).get("romanized", []))
    return found[:4]


def sounds(rows, head=None):
    """(prononciations, audio) : le pinyin tient la place de l'API."""
    audio = None
    for row in rows:
        for s in row.get("sounds") or []:
            if s.get("mp3_url") and "Mandarin" in (s.get("tags") or []):
                audio = s["mp3_url"]
                break
        if audio:
            break
    return pinyin_of(rows, head), audio


def extra(head, rows):
    group = GROUPS.get(head, {})
    forms = [group.get("traditional") or head, head] + group.get("variants", [])
    readings = hanviet(list(dict.fromkeys(f for f in forms if f)))
    for row in rows:
        for d in row.get("descendants") or []:
            w = d.get("word")
            if d.get("lang_code") == "vi" and w and not has_han(w) and \
                    w.lower() not in (r.lower() for r in readings):
                readings.append(w)
    # Le Wiktionnaire vietnamien range parfois des mots vietnamiens parmi
    # les dérivés d'un sinogramme (« văn minh » sous 明).
    derived = []
    for row in rows:
        for d in row.get("derived") or []:
            w = d.get("word") if isinstance(d, dict) else None
            if w and has_han(w) and w not in derived:
                derived.append(w)
    # Le wiki donne chaque dérivé dans les deux écritures ; le simplifié suffit.
    kept = set(derived)
    derived = [w for w in derived if simplify(w) == w or simplify(w) not in kept]
    out = {"derived": derived}
    if readings:
        out["hanviet"] = readings[:4]
    if group.get("traditional"):
        out["traditional"] = group["traditional"]
    if group.get("variants"):
        out["variants"] = group["variants"]
    return out


# --- l'index des formes ---------------------------------------------------------

# Un pinyin sans tons mène à beaucoup de mots : « shi » en a des centaines.
# On garde les plus fréquents.
MAX_LEMMAS = 30


def build(entries_by_head):
    """(forme tapée, vedette, analyse) pour chaque vedette gardée."""
    rank = frequency()
    by_form = collections.defaultdict(dict)
    n_script = n_pinyin = 0
    for head, rows in entries_by_head.items():
        group = GROUPS.get(head, {})
        for v in group.get("variants", []):
            trads = group.get("traditionals") or [group.get("traditional")]
            label_ = "phồn thể" if v in trads else "dị thể"
            by_form[v].setdefault(head, label_)
            n_script += 1
        count = sum(1 for c in head if is_han(c)) or len(head)
        for p in pinyin_of(rows, head):
            for form in pinyin_forms(p, count):
                if form != head:
                    by_form[form].setdefault(head, "bính âm")
                    n_pinyin += 1
    out = []
    for form, heads in by_form.items():
        ordered = sorted(heads, key=lambda h: (-rank.get(h), h))[:MAX_LEMMAS]
        out += [(form, h, heads[h]) for h in ordered]
    return out, f"{n_script:,} autres graphies, {n_pinyin:,} formes pinyin"


def redirects(by_word):
    """(graphie, vedette, analyse) pour les renvois qu'on n'affiche pas."""
    out = []
    for word, target, analysis in REFERENCES:
        head = HEAD_OF.get(target, target)
        if head != word and HEAD_OF.get(word) != head:
            out.append((word, head, analysis))
    return out
