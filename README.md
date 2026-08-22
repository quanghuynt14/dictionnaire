# dictionnaire

Un dictionnaire **français → vietnamien** qui ne demande rien à personne au
moment où on le consulte. Pas de modèle de langue, pas de requête réseau, pas de
clé d'API : le contenu est écrit par des humains, compilé une fois, et lu depuis
le disque.

Il sort par deux portes, du même fichier :

- **`Pháp–Việt.dictionary`** — un bundle pour Dictionary.app, consultable
  partout sur macOS avec ⌃⌘D.
- **une seed Mongo** pour le site *practice*. *(pas encore écrite — phase 3)*

## État

**Phase 0.** La chaîne complète marche, sur une coupe de trois mille lemmes.

```
2 987 entrées · 11 768 sens · 20 690 exemples · 27 259 clés · XML de 7,4 Mo
```

Ce qui est fait : récupération et verrouillage des sources, normalisation,
index des formes fléchies, émetteur XML, bundle Apple, les deux contrôles.
Ce qui ne l'est pas : l'émetteur Mongo, l'anglais, `make sync`.

## Faire tourner

```bash
make fetch            # les sources, et data/sources.lock qui dit lesquelles
make install          # → ~/Library/Dictionaries/Pháp-Việt.dictionary
make install TOP=all  # tout le dump plutôt que les 3 000 premiers lemmes
```

Puis, **une seule fois** : Dictionary.app > Réglages > cochez « Pháp–Việt », et
remontez-le au-dessus des dictionnaires d'Apple. Rien ne le consultera avant.

Sur Apple Silicon, les binaires du DDK sont x86_64 :
`softwareupdate --install-rosetta --agree-to-license`.

```bash
make check     # la clé est-elle dans le XML, et mène-t-elle au bon mot ?
make verify    # le bundle installé sait-il y répondre ?  ← celui qui compte
```

## Les sources

| Source | Ce qu'elle donne | Licence |
|---|---|---|
| [Wiktionnaire vietnamien](https://vi.wiktionary.org), section « Tiếng Pháp », extrait par [kaikki.org](https://kaikki.org/viwiktionary/) | 46 183 vedettes françaises, 79 558 sens **glosés en vietnamien**, 34 % avec exemples traduits | CC BY-SA 4.0 |
| [Lexique 3.83](http://www.lexique.org) | 125 653 formes fléchies → lemme + analyse, et la fréquence qui décide de la coupe | CC BY-SA 4.0 |

Les deux se repartagent aux mêmes conditions. Le bundle les cite dans
`DCSDictionaryCopyright` et dans son entrée « về từ điển này ».

**Ce que la source ne couvre pas.** Mesuré, pas supposé : sur les 3 000 lemmes
les plus fréquents du français, 89 % ont une entrée. Les 11 % manquants sont
presque tous des mots-outils — *je, le, ne, à, il, du, mais, se* — et **`faire`**,
que le Wiktionnaire vietnamien n'a tout simplement pas. C'est une limite de la
source, bornée et connue, et c'est à ça que sert `data/edits.jsonl`.

## base ⊕ edits

Un bundle `.dictionary` est compilé et en lecture seule : il n'existe pas de
mise à jour incrémentale. Toute correction veut dire recompiler. D'où le
découpage :

```
data/sources/     retéléchargeable, jamais dans git, épinglé par sources.lock
data/edits.jsonl  vos corrections, dans git, une ligne par entrée touchée
build/lexicon.jsonl   base ⊕ edits — ce que lisent les deux émetteurs
```

Une retouche est un patch de fusion par `id`. Une ligne dont l'`id` n'existe pas
crée l'entrée : c'est ainsi que `faire` est entré. **On n'y écrit que le sens** —
`fît`, `ferions`, `faisions` sont arrivées seules, par Lexique.

Les corrections faites depuis le site atterriront dans Mongo, et `make sync` les
rapatriera ici avant de reconstruire. La conséquence à accepter : une correction
est immédiate sur le site, et n'arrive dans Dictionary.app qu'au `sync` suivant.
Aucun découpage ne change ça — le bundle est compilé.

## Le découpage des entrées

**Une entrée par vedette, plusieurs clés par entrée** — l'inverse de
[conjugaison](../conjugaison), et pour une raison précise. Conjugaison indexe par
forme parce que sa réponse dépend de la forme tapée. Un dictionnaire n'a pas ce
problème : « allions » et « irions » veulent tous deux la page d'« aller ».
Apple sait faire, et `d:title` décide de l'étiquette dans la liste de résultats —
« allions (aller) ».

Ce que ça coûte : conjugaison produit 580 Mo de XML pour 2 000 verbes, parce que
chaque forme réémet le paradigme. Ici, 7,4 Mo pour 2 987 vedettes et 27 259 clés.

Les tableaux de conjugaison ne sont pas recopiés. Ils sont déjà installés sur la
même machine, dans « Conjugaison française », et la page renvoie à lui.

## Ce qui a été repris de conjugaison sans discuter

Ces quatre lignes ont chacune coûté une séance là-bas. Elles sont dans le
Makefile avec leur explication :

- `-v 10.11`, sinon les macOS récents ne lisent plus le bundle
- `preserve_unused_ref_id_in_reference_index=1`, sinon toute recherche ramène la
  première entrée du fichier
- `rm -rf` avant `ditto`, sinon macOS garde un index périmé et le dictionnaire
  disparaît de la fenêtre de consultation
- `pkill -f LookupViewService`, parce que `killall` ne reconnaît pas les services
  XPC et sort sans rien dire
