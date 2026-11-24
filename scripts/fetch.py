#!/usr/bin/env python3
"""Récupère les sources et écrit ce qu'on a récupéré dans data/sources.lock.

Le verrou n'est pas de la bureaucratie. Le bundle installé sur votre Mac est un
artefact compilé : quand une entrée a l'air fausse, la première question est
« de quel dump vient-elle ? ». Sans date ni empreinte, la réponse est une
supposition. Avec, c'est une ligne de fichier.

Usage :  python3 scripts/fetch.py [--force]
         python3 scripts/fetch.py --lang zh [--limit N]

Sans --lang, toutes les langues sauf les optionnelles (Trung–Việt). Avec,
cette langue seule, et le verrou garde ce qu'il savait des autres.
`--limit N` s'arrête après N lignes d'un dump filtré : un échantillon pour
travailler sur une petite machine. Il n'écrit pas le verrou.
"""

import hashlib
import importlib
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


def download_slim(src, force, limit=None):
    """Un dump trop gros pour le disque : filtré ligne à ligne en arrivant.

    Le fichier anglais du chinois pèse 1,2 Go, dont l'essentiel est du
    cantonais, du hokkien et des prononciations de dix dialectes. On ne
    l'écrit jamais en entier : `slim` (dans le module de morphologie, où
    vivent les décisions de contenu) rend la ligne allégée, ou None.

    L'empreinte notée est celle du dump **brut** : c'est elle qui dit de
    quel export kaikki vient le fichier.
    """
    dest = src["path"]
    if dest.exists() and not force and limit is None:
        print(f"  = {dest.name} déjà là")
        return None
    slim = importlib.import_module(src["slim"]).slim
    print(f"  ↓ {dest.name} (filtré)")
    h, size, raw, kept = hashlib.sha256(), 0, 0, 0
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(src["url"]) as r, open(tmp, "w", encoding="utf-8") as f:
        for line in r:
            h.update(line)
            size += len(line)
            raw += 1
            row = slim(json.loads(line)) if line.strip() else None
            if row:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                kept += 1
            if limit and raw >= limit:
                break
    tmp.replace(dest)
    print(f"    {raw:,} lignes lues, {kept:,} gardées")
    return {"url": src["url"], "sha256": h.hexdigest(), "bytes": size,
            "lines": raw, "kept": kept, "kept_sha256": digest(dest)}


def fetch_kaikki(src, force, limit=None):
    """Un dump kaikki, et ce que le verrou en dit."""
    if src.get("slim"):
        entry = download_slim(src, force, limit)
        if entry is None:
            # Déjà là : on garde ce que le verrou savait du dump brut.
            entry = json.loads(S.LOCK.read_text()).get(src["key"]) if S.LOCK.exists() else None
        return entry or {"url": src["url"], "kept_sha256": digest(src["path"])}
    download(src["url"], src["path"], force)
    return {
        "url": src["url"],
        "sha256": digest(src["path"]),
        "bytes": src["path"].stat().st_size,
        "lines": sum(1 for _ in open(src["path"], encoding="utf-8")),
    }


def fetch_zh(force, limit=None):
    """Trung–Việt : ses trois dumps, les lectures Hán Việt, la fréquence et
    la table traditionnel -> simplifié."""
    lock = {}
    cfg = S.lang("zh")
    for src in S.kaikki_sources("zh") + cfg.get("extra_sources", []):
        lock[src["key"]] = fetch_kaikki(src, force, limit)
    download(S.FREQ_ZH_URL, S.FREQ_ZH, force)
    lock["frequence-zh"] = {"url": S.FREQ_ZH_URL, "sha256": digest(S.FREQ_ZH)}
    download(S.OPENCC_TS_URL, S.OPENCC_TS, force)
    lock["opencc-ts"] = {"url": S.OPENCC_TS_URL, "sha256": digest(S.OPENCC_TS)}
    return lock


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
    argv = sys.argv[1:]
    force = "--force" in argv
    only = argv[argv.index("--lang") + 1] if "--lang" in argv else None
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    S.SOURCES.mkdir(parents=True, exist_ok=True)

    # Une langue seule : on complète le verrou au lieu de le réécrire.
    if only:
        S.lang(only)
        if only != "zh":
            sys.exit("--lang ne sert aujourd'hui qu'à zh.")
        fresh = fetch_zh(force, limit)
        if limit:
            print(f"\n  échantillon de {limit:,} lignes : sources.lock inchangé")
            return
        lock = json.loads(S.LOCK.read_text()) if S.LOCK.exists() else {}
        lock.update(fresh)
        S.LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print("\n  sources.lock complété")
        return

    lock = {}

    for code, cfg in S.LANGS.items():
        if cfg.get("optional"):
            continue
        for src in S.kaikki_sources(code):
            lock[src["key"]] = fetch_kaikki(src, force)

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

    # Vietnamien : la fréquence des syllabes.
    download(S.FREQ_VI_URL, S.FREQ_VI, force)
    lock["frequence-vi"] = {"url": S.FREQ_VI_URL, "sha256": digest(S.FREQ_VI)}

    # Le rattrapage, après les dumps : il a besoin d'eux pour savoir quelles
    # vedettes sont sans glose.
    for code, cfg in S.LANGS.items():
        if not cfg.get("rescue", True) or cfg.get("optional"):
            continue
        if force or not S.rescued(code).exists():
            print(f"  ↻ rattrapage {code}")
            subprocess.run([sys.executable, str(S.ROOT / "scripts" / "rescue.py"),
                            "--lang", code], check=True)
        else:
            print(f"  = rescued-{code}.jsonl déjà là")
        lock[f"rescued-{code}"] = {"sha256": digest(S.rescued(code))}

    # Les langues optionnelles gardent leur ligne du verrou précédent.
    if S.LOCK.exists():
        old = json.loads(S.LOCK.read_text())
        lock.update({k: v for k, v in old.items() if k not in lock})
    S.LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"\n  sources.lock écrit")
    for code, cfg in S.LANGS.items():
        if cfg.get("optional"):
            continue
        for src in S.kaikki_sources(code):
            print(f"    {src['key']} : {lock[src['key']]['lines']:,} lignes")


if __name__ == "__main__":
    main()
