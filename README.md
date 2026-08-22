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

**Phase 0.** La chaîne complète marche, sur tout le dump.

```
45 987 vedettes · 10 355 pages de forme ambiguë · 79 303 sens
45 995 exemples traduits · 240 137 formes fléchies · 280 436 clés
XML de 68 Mo · bundle de 55 Mo · normalisation 4 s · compilation DDK 2 min
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
| [Verbiste](http://sarrazip.com/dev/verbiste.html) | 146 modèles de conjugaison qui **engendrent** le paradigme complet de 7 011 verbes | GPL v2 |
| [Lexique 3.83](http://www.lexique.org) | les pluriels et les féminins, et la fréquence qui ordonne le dictionnaire | CC BY-SA 4.0 |

Le bundle les cite dans `DCSDictionaryCopyright` et dans son entrée
« về từ điển này ».

### Pourquoi Verbiste *et* Lexique

Lexique n'atteste que ce que ses corpus contiennent. Mesuré sur ses 6 399
verbes : **10,1 formes en moyenne**, là où un paradigme français en compte
environ quarante-cinq. 56 % des verbes sous les dix formes. Huit verbes au
complet, sur 6 399.

Concrètement : « allions » y figure sous *aller*, et nulle part sous *allier* —
dont Lexique ne connaît que treize formes. Or « nous allions » est du français
courant dans les deux sens. Un dictionnaire qu'on interroge en tapant la forme
qu'on vient de lire ne peut pas se permettre ce trou.

Verbiste est génératif : un modèle par famille, un radical par verbe, et les
quarante-cinq cases sortent — attestées ou non, ce qui est exactement ce qu'on
veut, puisque la question n'est pas « ce mot est-il fréquent » mais « qu'est-ce
que je viens de lire ».

D'où le partage : **les formes verbales viennent de Verbiste et de lui seul.**
Ce n'est pas qu'une question de complétude — Lexique porte aussi des erreurs de
lemmatisation sur les verbes (il range la forme « allier » sous le lemme
« aller »), et les mélanger ferait entrer ces erreurs dans l'index. Lexique
garde les noms, les adjectifs, et la fréquence, où il est bon.

Ce que ça change : l'index passe de 80 960 formes à **240 137**, dont 4 868
ambiguës. Ce sont les cas où le français est vraiment difficile —
« prises » mène à *pris*, *prise*, *prendre* et *priser*, et la liste de
résultats affiche les quatre.

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
chaque forme réémet le paradigme. Ici, 70 Mo pour 46 000 vedettes.

### Sauf pour les formes ambiguës, qui ont leur page

Une exception, et elle vient d'une mesure. La **fenêtre de survol** — ⌃⌘D, celle
qu'on utilise vraiment — ne rend qu'**une entrée par dictionnaire**.
`DCSCopyRecordsForSearchString` rendait bien les deux enregistrements de
« allions » ; `DCSCopyTextDefinition`, qui est ce que la fenêtre appelle, n'en
rendait qu'un — aller, parce qu'il sort le premier du fichier. La liste de
Dictionary.app montrait les deux mots. Le survol, jamais.

C'est la limite du découpage par vedette, et c'est exactement celle que
conjugaison contourne en découpant par forme : « le haut de la page ne peut pas
savoir quelle forme vous avez tapée ». On applique donc ce découpage-là, mais
seulement aux **3,7 % de clés qui en ont besoin** : une page par forme ambiguë,
qui possède la clé seule et rassemble tous les mots qu'elle atteint.

```
allions          2 mots
  aller          Đi.  « Aller à pied » — đi bộ
  allier         Pha, trộn (để chế hợp kim).  « Allier l'or avec l'argent »
```

L'analyse de la forme n'y est pas — « imparfait de l'indicatif, première
personne du pluriel ». La page répond à « quels mots est-ce que je viens de
lire », et deux vedettes y répondent. *Quelle case de quel verbe* est une autre
question, et elle a déjà son dictionnaire sur la même machine.

Même règle sur les entrées ordinaires : les formes fléchies d'un nom ou d'un
adjectif se lisent sur une ligne, sans leur analyse, à côté des synonymes et
des dérivés — c'est la même sorte de renvoi.

```
chat
  Danh từ    Mèo
  Danh từ    Trò chuyện, tán gẫu
  Các dạng   chats, chatte, chattes
  Đồng nghĩa tchat
  Cụm từ     à bon chat, bon rat, avoir un chat dans la gorge…  +47
```

10 355 pages, 5 020 vedettes absorbées, et le corps duplique 9,4 Mo. Les 96,3 %
restants ne bougent pas : leur clé reste sur la vedette, leur corps n'est écrit
qu'une fois. Depuis, **une clé n'appartient qu'à une entrée** — c'est ce que
`make check` vérifie, avec la contrepartie qu'aucune vedette ne doit devenir
inatteignable.

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
