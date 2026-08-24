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
import sys

import sources as S

# La langue cible, côté practice. Ses constantes sont des noms anglais en
# minuscules — voir packages/shared/src/constants.ts.
TARGET = "vietnamese"
SOURCE_OF = {"fr": "french", "en": "english"}


def translated_of(entry):
    """La ligne courte en haut de la page : les premières gloses, séparées.

    practice appelle ce champ `translated` et l'affiche seul dans les listes
    — historique, favoris, reels. Il lui faut donc quelque chose de court et
    qui se suffise : les premières gloses de chaque catégorie, pas la première
    glose tout court, sinon un mot qui est nom *et* verbe ne montre que l'un
    des deux.
    """
    out = []
    for block in entry.get("blocks", []):
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
                {"sourceSentence": ex["src"], "targetTranslation": ex["vi"]}
                for ex in sense.get("examples", []) if ex.get("vi")
            ]
            explain = sense.get("gloss", "")
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

    lexicon = [json.loads(l) for l in
               open(S.BUILD / f"lexicon-{code}.jsonl", encoding="utf-8") if l.strip()]
    forms = json.load(open(S.BUILD / f"forms-{code}.json", encoding="utf-8"))
    heads = {e["headword"] for e in lexicon}

    out = S.BUILD / f"mongo-{code}.ndjson"
    n_words = n_forms = 0
    with open(out, "w", encoding="utf-8") as f:
        for entry in lexicon:
            explains = explains_of(entry)
            if not explains:
                continue
            n_words += 1
            f.write(json.dumps({
                "_collection": "dictionary",
                "word": entry["headword"],
                "sourceLanguage": source,
                "targetLanguage": TARGET,
                "translated": translated_of(entry),
                "explains": explains,
                # Ce que la version LLM n'avait pas, et qui vient de la source.
                "ipa": entry.get("ipa") or [],
                "audio": entry.get("audio"),
                "wiki": entry.get("wiki"),
                "derived": (entry.get("derived") or [])[:12],
                "rank": entry.get("rank", 0.0),
                "edited": bool(entry.get("edited")),
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
    print(f"  → {out.relative_to(S.ROOT)} ({size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
