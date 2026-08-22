#!/usr/bin/env python3
"""Récupère les sources et écrit ce qu'on a récupéré dans data/sources.lock.

Le verrou n'est pas de la bureaucratie. Le bundle installé sur votre Mac est un
artefact compilé : quand une entrée a l'air fausse, la première question est
« de quel dump vient-elle ? ». Sans date ni empreinte, la réponse est une
supposition. Avec, c'est une ligne de fichier.

Usage :  python3 scripts/fetch.py [--force]
"""

import hashlib
import json
import shutil
import sys
import urllib.request

import sources as S


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    print(f"  ↓ {dest.name}")
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def main():
    force = "--force" in sys.argv
    S.SOURCES.mkdir(parents=True, exist_ok=True)

    if force or not S.KAIKKI_FR.exists():
        download(S.KAIKKI_FR_URL, S.KAIKKI_FR)
    else:
        print(f"  = {S.KAIKKI_FR.name} déjà là (--force pour retélécharger)")

    # Lexique vient du dépôt voisin plutôt que du réseau : conjugaison l'a déjà,
    # il pèse vingt-cinq mégaoctets, et les deux dictionnaires doivent parler de
    # la même morphologie. Deux copies d'un même fichier qui divergent, c'est un
    # bug qu'on ne verrait jamais.
    if force or not S.LEXIQUE.exists():
        if not S.LEXIQUE_FROM.exists():
            sys.exit(f"Lexique383.tsv introuvable dans {S.LEXIQUE_FROM}.\n"
                     "Récupérez-le sur http://www.lexique.org et posez-le là.")
        print(f"  ← {S.LEXIQUE_FROM}")
        shutil.copy2(S.LEXIQUE_FROM, S.LEXIQUE)
    else:
        print(f"  = {S.LEXIQUE.name} déjà là")

    for name in ("verbs-fr.xml", "conjugations-fr.xml"):
        dest = S.SOURCES / name
        if force or not dest.exists():
            src = S.VERBISTE_FROM / name
            if not src.exists():
                sys.exit(f"{name} introuvable dans {S.VERBISTE_FROM}.")
            print(f"  ← {src}")
            shutil.copy2(src, dest)
        else:
            print(f"  = {name} déjà là")

    lock = {
        "kaikki-fr": {
            "url": S.KAIKKI_FR_URL,
            "sha256": digest(S.KAIKKI_FR),
            "bytes": S.KAIKKI_FR.stat().st_size,
            "lines": sum(1 for _ in open(S.KAIKKI_FR, encoding="utf-8")),
        },
        "lexique": {
            "from": str(S.LEXIQUE_FROM),
            "sha256": digest(S.LEXIQUE),
            "bytes": S.LEXIQUE.stat().st_size,
        },
        "verbiste": {
            "from": str(S.VERBISTE_FROM),
            "verbs-fr.xml": digest(S.VERBS),
            "conjugations-fr.xml": digest(S.CONJUGATIONS),
        },
    }
    S.LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"\n  sources.lock écrit — {lock['kaikki-fr']['lines']} lignes kaikki")


if __name__ == "__main__":
    main()
