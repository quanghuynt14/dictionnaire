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

import collections
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
    out = [(head,
            f'  <d:index d:value="{html.escape(head)}" d:title="{html.escape(head)}"/>')]
    for form in entry.get("forms", []):
        if form == head:
            continue
        out.append((form,
                    f'  <d:index d:value="{html.escape(form)}" '
                    f'd:title="{html.escape(form)} ({html.escape(head)})"/>'))
    return out


def blocks_html(entry, indent="    "):
    """Les sections d'une entrée — sans son <h1>, pour pouvoir la rendre aussi
    à l'intérieur d'une page de forme ambiguë."""
    p = []
    for block in entry["blocks"]:
        label = block.get("pos_vi") or block.get("pos") or ""
        p.append(f'{indent}<div class="block">')
        if label:
            p.append(f'{indent}  <div class="pos">{e(label)}</div>')
        p.append(f'{indent}  <ol class="senses">')
        for sense in block["senses"]:
            p.append(f'{indent}    <li class="sense">')
            p.append(f'{indent}      <span class="gloss">{e(sense["gloss"])}</span>')
            for extra in sense.get("sub", []):
                p.append(f'{indent}      <span class="sub">{e(extra)}</span>')
            if sense.get("examples"):
                p.append(f'{indent}      <ul class="examples">')
                for ex in sense["examples"]:
                    vi = (f'<span class="ex-vi">{e(ex["vi"])}</span>'
                          if ex.get("vi") else "")
                    p.append(f'{indent}        <li><span class="ex-fr">{e(ex["fr"])}</span>{vi}</li>')
                p.append(f'{indent}      </ul>')
            p.append(f'{indent}    </li>')
        p.append(f'{indent}  </ol>')
        p.append(f'{indent}</div>')
    return p


def body(entry, forms_index):
    head = entry["headword"]
    p = [f'  <div class="entry">',
         f'    <h1 class="headword">{e(head)}</h1>']

    if entry.get("ipa"):
        p.append(f'    <span class="ipa">{e(" ".join(entry["ipa"]))}</span>')

    p += blocks_html(entry)

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


def merged_body(form, members, forms_index):
    """La page d'une forme qui mène à plusieurs mots.

    Pourquoi elle existe. La fenêtre de survol — ⌃⌘D, celle qu'on utilise
    vraiment — ne rend **qu'une entrée par dictionnaire**. Mesuré :
    DCSCopyRecordsForSearchString rend bien les deux enregistrements de
    « allions », et DCSCopyTextDefinition n'en rend qu'un, celui d'aller, parce
    qu'il sort le premier du fichier. La liste de Dictionary.app montrait les
    deux ; le survol, jamais.

    C'est la limite du découpage par vedette, et c'est exactement celle que
    conjugaison contourne en découpant par forme : « le haut de la page ne peut
    pas savoir quelle forme vous avez tapée ». Ici on n'applique ce découpage
    qu'aux 3,7 % de clés qui en ont besoin — une page par forme ambiguë, qui
    possède la clé et rassemble tous les mots qu'elle atteint.

    Les autres 96,3 % ne bougent pas : leur clé reste sur la vedette, et le
    corps n'est écrit qu'une fois.
    """
    p = ['  <div class="entry">',
         f'    <h1 class="headword">{e(form)}</h1>',
         f'    <div class="ambig">{len(members)} mots</div>']
    for entry, how in members:
        head = entry["headword"]
        p.append('    <div class="member">')
        p.append(f'      <h2 class="member-head">{e(head)}</h2>')
        if how:
            p.append(f'      <div class="member-how">{e(how)}</div>')
        p += blocks_html(entry, indent="      ")
        p.append('    </div>')
    p.append('  </div>')
    return p


def plan_keys(lexicon):
    """clé -> [(entrée, analyse)] — qui répond à quoi, avant d'écrire quoi que ce soit.

    Il faut ce plan complet avant la première ligne de XML : on ne sait qu'une
    clé est ambiguë qu'après avoir vu toutes les entrées qui la portent.
    """
    keys = collections.defaultdict(list)
    for entry in lexicon:
        head = entry["headword"]
        keys[head].append((entry, None))
        for form in entry.get("forms", []):
            if form != head:
                keys[form].append((entry, form))
    return keys


def main():
    lexicon = [json.loads(l) for l in
               open(S.BUILD / "lexicon.jsonl", encoding="utf-8") if l.strip()]
    forms_index = json.load(open(S.BUILD / "forms.json", encoding="utf-8"))

    keys = plan_keys(lexicon)
    ambiguous = {k: v for k, v in keys.items() if len(v) > 1}

    seen = set()
    n_keys = n_dropped = 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(HEADER)

        # Les pages de formes ambiguës d'abord. Elles possèdent leur clé seules :
        # la laisser aussi sur les vedettes ferait trois lignes dans la liste de
        # résultats pour « allions », dont deux mèneraient à une moitié de la
        # réponse.
        for form, members in sorted(ambiguous.items()):
            eid = "a_" + entry_id(form)[2:]
            with_how = [(entry, next((x["analysis"]
                                      for x in forms_index.get(form, [])
                                      if x["lemma"] == entry["headword"]), None)
                         if via else None)
                        for entry, via in members]
            f.write(f'<d:entry id="{eid}" d:title="{html.escape(form)}">\n')
            f.write(f'  <d:index d:value="{html.escape(form)}" '
                    f'd:title="{html.escape(form)}"/>\n')
            n_keys += 1
            f.write("\n".join(merged_body(form, with_how, forms_index)) + "\n")
            f.write("</d:entry>\n")

        for entry in lexicon:
            eid = entry_id(entry["headword"])
            if eid in seen:
                continue
            idx = [line for form, line in indexes(entry, forms_index)
                   if form not in ambiguous]
            # Une entrée dont toutes les clés sont parties n'est plus
            # atteignable — et n'a plus à l'être : son contenu est recopié dans
            # les pages de forme qui ont pris ses clés.
            if not idx:
                n_dropped += 1
                continue
            seen.add(eid)
            f.write(f'<d:entry id="{eid}" d:title="{html.escape(entry["headword"])}">\n')
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
        f.write(f'    <div class="about"><div>{len(seen) + len(ambiguous)} mục từ · {n_keys} khoá '
                f'· {n_edits} sửa tay</div>\n')
        f.write(f'    <div>Dựng lúc {stamp}</div>\n')
        f.write(f'    <div>kaikki sha256 {e(lock.get("kaikki-fr", {}).get("sha256", "?")[:12])}</div>\n')
        for credit in S.ATTRIBUTION.values():
            f.write(f'    <div class="credit">{e(credit)}</div>\n')
        f.write('    </div></div>\n</d:entry>\n')
        f.write("</d:dictionary>\n")

    size = OUT.stat().st_size
    print(f"  {len(seen)} entrées + {len(ambiguous)} pages de forme ambiguë "
          f"({n_dropped} entrées absorbées), {n_keys} clés")
    print(f"  → {OUT.relative_to(S.ROOT)} ({size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
