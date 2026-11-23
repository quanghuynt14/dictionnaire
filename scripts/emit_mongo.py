#!/usr/bin/env python3
"""build/lexicon-LL.jsonl -> build/mongo-LL.ndjson, la seed du site.

Le second shell. Le premier écrit du XML pour le compilateur d'Apple ; celui-ci
écrit des documents pour Mongo. Les deux lisent le **même** lexicon.jsonl, ce
qui est tout l'intérêt : la fenêtre de Dictionary.app et le site ne peuvent pas
diverger, puisqu'ils sortent du même fichier.

Ce script n'ouvre aucune connexion. Il écrit du NDJSON, et c'est practice qui
l'ingère avec son propre pilote et ses propres identifiants — le dictionnaire
décide du contenu, l'application décide de sa base.

Deux collections :

  dictionary        une vedette par document, dans la forme que practice lit
                    déjà. C'est délibéré : l'historique et les favoris pointent
                    des `_id` de cette collection, et changer sa forme les
                    casserait tous. On la remplit, on ne la refait pas.

  dictionary_forms  forme fléchie -> vedettes. C'est ce qui manquait au site :
                    « allions » n'y donnait rien, alors que le bundle Apple le
                    sait depuis Verbiste.

Usage :  python3 scripts/emit_mongo.py --lang fr
"""

import json
import re
import sys

import sources as S

# Les langues, côté practice. Ses constantes sont des noms anglais en
# minuscules — voir packages/shared/src/constants.ts.
SOURCE_OF = {"fr": "french", "en": "english", "vi": "vietnamese"}
TARGET_OF = {"fr": "vietnamese", "en": "vietnamese", "vi": "french"}

# Việt–Pháp mêle deux langues de glose : le français, et l'anglais là où le
# Wiktionnaire français se tait ou date. Un sens anglais porte cette marque,
# pour qu'on ne le prenne pas pour du français.
FOREIGN_MARK = {"en": "EN"}


def own_entries(code):
    """Les entrées reindoo, par mot. Seul Việt–Pháp en a, voir
    import_reindoo.py."""
    path = S.ROOT / "data" / f"reindoo-{code}.jsonl"
    if not path.exists():
        return {}
    return {e["word"]: e for e in map(json.loads, open(path, encoding="utf-8")) if e}


def own_explains(own):
    """Les sens reindoo, dans la forme `explains`, avec deux champs de plus.

    `note` porte ce qu'un francophone se trompe à faire ; `source` les
    distingue des sens du Wiktionnaire, que l'app affiche à part, en dessous.
    Les étiquettes suivent la catégorie, comme [EN] : « (Verbe) [Nord] … ».
    """
    out = []
    for sense in own["senses"]:
        labels = "".join(f"[{l}] " for l in sense["labels"])
        explain = f"({sense['pos']}) {labels}{sense['gloss']}"
        item = {
            "explain": explain,
            "synonyms": [],
            "antonyms": [],
            "exampleSentences": [{"sourceSentence": ex["src"], "targetTranslation": ex["tr"]}
                                 for ex in sense["examples"]],
            "source": "reindoo",
        }
        if sense.get("note"):
            item["note"] = sense["note"]
        out.append(item)
    return out


def own_translated(own):
    """La ligne courte, tirée des trois premiers sens, sans leurs précisions
    entre parenthèses : « être / alors, et / rien que, que des »."""
    out = []
    for sense in own["senses"]:
        gloss = re.sub(r"\s*\([^)]*\)", "", sense["gloss"]).strip(" ,;")
        if gloss and gloss not in out:
            out.append(gloss)
    return " / ".join(out[:3])


def target_blocks(entry, code):
    """Les blocs dans la langue cible, ou tous s'il n'y en a aucun."""
    blocks = entry.get("blocks", [])
    wanted = TARGET_OF[code][:2]
    own = [b for b in blocks if b.get("gloss_lang", "vi") == wanted]
    return own or blocks


def translated_of(entry, code):
    """La ligne courte en haut de la page : les premières gloses, séparées.

    practice appelle ce champ `translated` et l'affiche seul dans les listes
    — historique, favoris, reels. Il lui faut donc quelque chose de court et
    qui se suffise : les premières gloses de chaque catégorie, pas la première
    glose tout court, sinon un mot qui est nom *et* verbe ne montre que l'un
    des deux.

    Pour Việt–Pháp, la ligne est en français dès qu'un sens français existe ;
    l'anglais ne la remplit que pour les mots que le Wiktionnaire français
    n'a pas.
    """
    out = []
    for block in target_blocks(entry, code):
        senses = block.get("senses") or []
        if senses and senses[0].get("gloss"):
            gloss = senses[0]["gloss"].rstrip(".")
            if gloss not in out:
                out.append(gloss)
    return " / ".join(out[:3])


def explains_of(entry):
    """Les sens, dans la forme `explains` que practice lit déjà.

    Les synonymes et les antonymes sont portés par l'entrée chez nous, pas par
    le sens. On les met sur le premier sens plutôt que de les répéter partout :
    répétés, ils donneraient l'impression d'être propres à chaque acception.

    Un exemple sans traduction est écarté. Le schéma de réponse de practice
    exige les deux champs, et remplir `targetTranslation` d'une chaîne vide
    afficherait une ligne vide sous la phrase source.
    """
    out = []
    first = True
    for block in entry.get("blocks", []):
        for sense in block.get("senses", []):
            examples = [
                {"sourceSentence": ex["src"], "targetTranslation": ex["tr"]}
                for ex in sense.get("examples", []) if ex.get("tr")
            ]
            explain = sense.get("gloss", "")
            mark = FOREIGN_MARK.get(block.get("gloss_lang"))
            if mark:
                explain = f"[{mark}] {explain}"
            # La catégorie grammaticale devant le sens : « Danh từ » contre
            # « Ngoại động từ » est souvent ce qui sépare deux acceptions, et
            # `explains` n'a pas de champ pour la porter.
            if block.get("pos_vi"):
                explain = f"({block['pos_vi']}) {explain}"
            out.append({
                "explain": explain,
                "synonyms": (entry.get("synonyms") or [])[:2] if first else [],
                "antonyms": (entry.get("antonyms") or [])[:2] if first else [],
                "exampleSentences": examples[:4],
            })
            first = False
    return out


def main():
    argv = sys.argv[1:]
    code = argv[argv.index("--lang") + 1] if "--lang" in argv else "fr"
    cfg = S.lang(code)
    source = SOURCE_OF[code]
    target = TARGET_OF[code]

    lexicon = [json.loads(l) for l in
               open(S.BUILD / f"lexicon-{code}.jsonl", encoding="utf-8") if l.strip()]
    forms = json.load(open(S.BUILD / f"forms-{code}.json", encoding="utf-8"))
    heads = {e["headword"] for e in lexicon}
    own = own_entries(code)
    missing = sorted(set(own) - heads)
    if missing:
        raise SystemExit(f"entrées reindoo sans vedette : {missing[:10]}")

    out = S.BUILD / f"mongo-{code}.ndjson"
    n_words = n_forms = 0
    with open(out, "w", encoding="utf-8") as f:
        for entry in lexicon:
            explains = explains_of(entry)
            mine = own.get(entry["headword"])
            if mine:
                explains = own_explains(mine) + explains
            if not explains:
                continue
            n_words += 1
            f.write(json.dumps({
                "_collection": "dictionary",
                "word": entry["headword"],
                "sourceLanguage": source,
                "targetLanguage": target,
                "translated": own_translated(mine) if mine else translated_of(entry, code),
                "explains": explains,
                # Ce que la version LLM n'avait pas, et qui vient de la source.
                "ipa": entry.get("ipa") or [],
                "audio": entry.get("audio"),
                "wiki": entry.get("wiki"),
                "wikis": entry.get("wikis") or [],
                "derived": (entry.get("derived") or [])[:12],
                "rank": entry.get("rank", 0.0),
                "edited": bool(entry.get("edited")),
                # Ce qui aide à retenir le mot, quand quelqu'un l'a écrit.
                **({"memo": entry["memo"]} if entry.get("memo") else {}),
            }, ensure_ascii=False) + "\n")

        for form, targets in forms.items():
            lemmas = [t["lemma"] for t in targets if t["lemma"] in heads]
            if not lemmas:
                continue
            # On garde aussi les formes qui sont elles-mêmes des vedettes, et
            # c'est mesuré. Le Wiktionnaire vietnamien donne à « went » sa
            # propre entrée, dont la glose entière est « động từ quá khứ của
            # go » — un renvoi, pas un sens. La recherche directe la trouvait,
            # s'arrêtait là, et le lecteur repartait sans savoir ce que « go »
            # veut dire. La table des formes est ce qui permet de rattacher les
            # deux, comme la page de forme ambiguë le fait dans le bundle.
            lemmas = [l for l in lemmas if l != form]
            if not lemmas:
                continue
            n_forms += 1
            f.write(json.dumps({
                "_collection": "dictionary_forms",
                "form": form,
                "sourceLanguage": source,
                "lemmas": lemmas,
                "analysis": targets[0].get("analysis"),
            }, ensure_ascii=False) + "\n")

    size = out.stat().st_size
    print(f"  {cfg['name']} : {n_words:,} vedettes + {n_forms:,} formes")
    if own:
        print(f"  dont {len(own):,} avec une entrée reindoo en tête")
    print(f"  → {out.relative_to(S.ROOT)} ({size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
