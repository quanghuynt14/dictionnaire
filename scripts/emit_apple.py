#!/usr/bin/env python3
"""build/lexicon.jsonl -> src/phap-viet.xml, la source que compile le DDK d'Apple.

Le découpage, et c'est tout le sujet : **une entrée par vedette, plusieurs clés
par entrée**. C'est l'inverse de conjugaison, et pour une raison précise.

Conjugaison indexe par *forme* parce que sa réponse dépend de la forme tapée :
« vis » ouvre une page qui commence par dire ce que « vis » peut être. Un
dictionnaire n'a pas ce problème — « allions » et « allons » veulent la même
page, celle d'« aller ». Apple sait faire : plusieurs <d:index> pointent la même
entrée, et `d:title` décide de ce qu'affiche la liste de résultats. C'est le
modèle de l'exemple livré avec le DDK, où « made » s'affiche « made (make) ».

Ce qu'on y gagne : conjugaison produit 580 Mo de XML pour deux mille verbes,
parce que chaque forme réémet le paradigme entier. Ici le corps est écrit une
fois par vedette et les formes ne coûtent qu'une ligne d'index chacune.

Ce qu'on n'écrit pas : les tableaux de conjugaison. Ils sont déjà installés sur
la même machine, dans « Conjugaison française », et un mot cherché dans l'un
s'ouvre dans l'autre. Recopier deux mille paradigmes ici ne ferait que créer une
seconde vérité à maintenir.

Usage :  python3 scripts/emit_apple.py
"""

import hashlib
import html
import json

import sources as S

OUT = S.ROOT / "src" / "phap-viet.xml"

HEADER = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<d:dictionary xmlns="http://www.w3.org/1999/xhtml" '
          'xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">\n')

# Les formes fléchies qu'on liste dans la page. Un verbe en a plus de quarante
# et elles ont déjà leur dictionnaire ; un nom en a une ou deux et personne ne
# va les chercher ailleurs.
MAX_FORMS_SHOWN = 6


def e(text):
    return html.escape(text or "", quote=False)


def entry_id(headword):
    """Un identifiant stable, lisible, et valide comme id XML.

    Le hash n'est pas de la superstition : « à-côté » et « œuf » ne font pas des
    id valides, et deux vedettes peuvent se réduire au même squelette ASCII.
    """
    slug = "".join(c if c.isalnum() else "_" for c in headword)[:24]
    return f"e_{slug}_{hashlib.sha1(headword.encode()).hexdigest()[:6]}"


def indexes(entry, forms_index):
    """La vedette, puis chaque forme fléchie qui doit y mener.

    `d:title` est ce que montre la liste de résultats. Pour une forme fléchie on
    y écrit la vedette entre parenthèses : sans ça, chercher « allions » affiche
    une ligne « allions » et il faut cliquer pour savoir sur quel verbe on tombe.
    """
    head = entry["headword"]
    out = [f'  <d:index d:value="{html.escape(head)}" d:title="{html.escape(head)}"/>']
    for form in entry.get("forms", []):
        if form == head:
            continue
        out.append(f'  <d:index d:value="{html.escape(form)}" '
                   f'd:title="{html.escape(form)} ({html.escape(head)})"/>')
    return out


def body(entry, forms_index):
    head = entry["headword"]
    p = [f'  <div class="entry">',
         f'    <h1 class="headword">{e(head)}</h1>']

    if entry.get("ipa"):
        p.append(f'    <span class="ipa">{e(" ".join(entry["ipa"]))}</span>')

    for block in entry["blocks"]:
        label = block.get("pos_vi") or block.get("pos") or ""
        p.append('    <div class="block">')
        if label:
            p.append(f'      <div class="pos">{e(label)}</div>')
        p.append('      <ol class="senses">')
        for sense in block["senses"]:
            p.append('        <li class="sense">')
            p.append(f'          <span class="gloss">{e(sense["gloss"])}</span>')
            for extra in sense.get("sub", []):
                p.append(f'          <span class="sub">{e(extra)}</span>')
            if sense.get("examples"):
                p.append('          <ul class="examples">')
                for ex in sense["examples"]:
                    vi = (f'<span class="ex-vi">{e(ex["vi"])}</span>'
                          if ex.get("vi") else "")
                    p.append(f'            <li><span class="ex-fr">{e(ex["fr"])}</span>{vi}</li>')
                p.append('          </ul>')
            p.append('        </li>')
        p.append('      </ol>')
        p.append('    </div>')

    # Les formes fléchies, mais seulement quand elles tiennent. Le seuil vaut
    # aussi comme test : un mot qui dépasse six formes est un verbe, et un verbe
    # renvoie au dictionnaire qui fait ça.
    shown = [f for f in entry.get("forms", []) if f != head]
    if shown and len(shown) <= MAX_FORMS_SHOWN:
        p.append('    <div class="forms">')
        for form in shown:
            how = next((x["analysis"] for x in forms_index.get(form, [])
                        if x["lemma"] == head), None)
            p.append(f'      <div class="form-row"><span class="form">{e(form)}</span>'
                     f'<span class="form-how">{e(how or "")}</span></div>')
        p.append('    </div>')
    elif shown:
        p.append('    <div class="forms-ref">Conjugaison complète : '
                 '« Conjugaison française ».</div>')

    for key, label in (("synonyms", "Đồng nghĩa"), ("antonyms", "Trái nghĩa"),
                       ("derived", "Cụm từ"), ("related", "Liên quan")):
        words = entry.get(key) or []
        if not words:
            continue
        # Les dérivés d'un mot courant se comptent par dizaines — « langue » en a
        # quarante-quatre. Au-delà de douze la liste cesse d'être lisible dans une
        # fenêtre de 300 px et devient un mur.
        shown_w = words[:12]
        rest = len(words) - len(shown_w)
        tail = f" +{rest}" if rest > 0 else ""
        p.append(f'    <div class="rel"><span class="rel-label">{label}</span>'
                 f'<span class="rel-words">{e(", ".join(shown_w))}{tail}</span></div>')

    if entry.get("edited"):
        p.append('    <div class="edited">Mục từ đã được sửa tay.</div>')

    p.append('  </div>')
    return p


def main():
    lexicon = [json.loads(l) for l in
               open(S.BUILD / "lexicon.jsonl", encoding="utf-8") if l.strip()]
    forms_index = json.load(open(S.BUILD / "forms.json", encoding="utf-8"))

    seen = set()
    n_keys = 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(HEADER)
        for entry in lexicon:
            eid = entry_id(entry["headword"])
            if eid in seen:
                continue
            seen.add(eid)
            f.write(f'<d:entry id="{eid}" d:title="{html.escape(entry["headword"])}">\n')
            idx = indexes(entry, forms_index)
            n_keys += len(idx)
            f.write("\n".join(idx) + "\n")
            f.write("\n".join(body(entry, forms_index)) + "\n")
            f.write("</d:entry>\n")

        # Le tampon de fabrication. Une entrée, cherchable, qui dit de quel dump
        # et de quelle date sort le bundle qu'on a sous les yeux. Sans elle, la
        # question « est-ce que ma retouche est arrivée ? » n'a pas de réponse
        # qu'on puisse lire dans Dictionary.app.
        lock = json.loads(S.LOCK.read_text(encoding="utf-8")) if S.LOCK.exists() else {}
        import datetime
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        n_edits = sum(1 for x in lexicon if x.get("edited"))
        f.write('<d:entry id="e_about" d:title="về từ điển này">\n')
        f.write('  <d:index d:value="về từ điển này" d:title="về từ điển này"/>\n')
        f.write('  <d:index d:value="Pháp-Việt" d:title="về từ điển này"/>\n')
        f.write('  <div class="entry"><h1 class="headword">Pháp–Việt</h1>\n')
        f.write(f'    <div class="about"><div>{len(lexicon)} mục từ · {n_keys} khoá '
                f'· {n_edits} sửa tay</div>\n')
        f.write(f'    <div>Dựng lúc {stamp}</div>\n')
        f.write(f'    <div>kaikki sha256 {e(lock.get("kaikki-fr", {}).get("sha256", "?")[:12])}</div>\n')
        for credit in S.ATTRIBUTION.values():
            f.write(f'    <div class="credit">{e(credit)}</div>\n')
        f.write('    </div></div>\n</d:entry>\n')
        f.write("</d:dictionary>\n")

    size = OUT.stat().st_size
    print(f"  {len(seen)} entrées, {n_keys} clés → {OUT.relative_to(S.ROOT)} "
          f"({size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
