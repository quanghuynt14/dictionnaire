#!/usr/bin/env python3
"""Récupère les sources et écrit ce qu'on a récupéré dans data/sources.lock.

Le verrou n'est pas de la bureaucratie. Le bundle installé sur votre Mac est un
artefact compilé : quand une entrée a l'air fausse, la première question est
« de quel dump vient-elle ? ». Sans date ni empreinte, la réponse est une
supposition. Avec, c'est une ligne de fichier.

Usage :  python3 scripts/fetch.py [--force]
"""

import hashlib
import io
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile

import sources as S


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, force):
    if dest.exists() and not force:
        print(f"  = {dest.name} déjà là")
        return
    print(f"  ↓ {dest.name}")
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def copy_from(src, dest, force):
    if dest.exists() and not force:
        print(f"  = {dest.name} déjà là")
        return
    if not src.exists():
        sys.exit(f"{src} introuvable.")
    print(f"  ← {src}")
    shutil.copy2(src, dest)


def fetch_wordnet(force):
    """Les quatre fichiers d'exceptions, extraits de l'archive de nltk.

    On ne garde que les .exc — quatre-vingt-dix kilo-octets sur onze mégas. Le
    reste de WordNet est une base de synsets dont ce projet n'a pas l'usage :
    les sens viennent du Wiktionnaire vietnamien, pas d'ici.
    """
    S.WORDNET_EXC.mkdir(parents=True, exist_ok=True)
    if not force and all((S.WORDNET_EXC / f"{n}.exc").exists()
                         for n in ("noun", "verb", "adj", "adv")):
        print("  = exceptions WordNet déjà là")
        return
    print("  ↓ wordnet.zip")
    with urllib.request.urlopen(S.WORDNET_URL) as r:
        blob = io.BytesIO(r.read())
    with zipfile.ZipFile(blob) as z:
        for member in z.namelist():
            if member.endswith(".exc"):
                name = member.rsplit("/", 1)[-1]
                (S.WORDNET_EXC / name).write_bytes(z.read(member))


def main():
    force = "--force" in sys.argv
    S.SOURCES.mkdir(parents=True, exist_ok=True)

    lock = {}

    for code, cfg in S.LANGS.items():
        download(cfg["kaikki_url"], cfg["kaikki"], force)
        lock[f"kaikki-{code}"] = {
            "url": cfg["kaikki_url"],
            "sha256": digest(cfg["kaikki"]),
            "bytes": cfg["kaikki"].stat().st_size,
            "lines": sum(1 for _ in open(cfg["kaikki"], encoding="utf-8")),
        }

    # Français : Verbiste et Lexique viennent du dépôt voisin. Les deux projets
    # doivent parler de la même morphologie ; deux copies qui divergent seraient
    # un bug qu'on ne verrait jamais.
    for name in ("Lexique383.tsv", "verbs-fr.xml", "conjugations-fr.xml"):
        copy_from(S.CONJUGAISON / name, S.SOURCES / name, force)
    lock["lexique"] = {"from": str(S.CONJUGAISON), "sha256": digest(S.LEXIQUE)}
    lock["verbiste"] = {"verbs": digest(S.VERBS),
                        "conjugations": digest(S.CONJUGATIONS)}

    # Anglais : les irréguliers et la fréquence.
    fetch_wordnet(force)
    download(S.SUBTLEX_URL, S.SUBTLEX, force)
    lock["wordnet"] = {n: digest(S.WORDNET_EXC / f"{n}.exc")
                       for n in ("noun", "verb", "adj", "adv")}
    lock["frequence-en"] = {"url": S.SUBTLEX_URL, "sha256": digest(S.SUBTLEX)}

    # Le rattrapage, après les dumps : il a besoin d'eux pour savoir quelles
    # vedettes sont sans glose.
    for code in S.LANGS:
        if force or not S.rescued(code).exists():
            print(f"  ↻ rattrapage {code}")
            subprocess.run([sys.executable, str(S.ROOT / "scripts" / "rescue.py"),
                            "--lang", code], check=True)
        else:
            print(f"  = rescued-{code}.jsonl déjà là")
        lock[f"rescued-{code}"] = {"sha256": digest(S.rescued(code))}

    S.LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"\n  sources.lock écrit")
    for code in S.LANGS:
        print(f"    kaikki-{code} : {lock[f'kaikki-{code}']['lines']:,} lignes")


if __name__ == "__main__":
    main()
