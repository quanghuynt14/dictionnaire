# dictionnaire

Deux dictionnaires **vers le vietnamien** qui ne demandent rien à personne au
moment où on les consulte. Pas de modèle de langue, pas de requête réseau, pas
de clé d'API : le contenu est écrit par des humains, compilé une fois, et lu
depuis le disque.

Ils sortent du même code, par deux portes :

- **`Pháp–Việt.dictionary`** et **`Anh–Việt.dictionary`** — des bundles pour
  Dictionary.app, consultables partout sur macOS avec ⌃⌘D.
- **une seed Mongo** pour le site *practice*, via `make mongo`.

## État

**Phase 0 terminée**, sur tout le dump, dans les deux langues.

| | Pháp–Việt | Anh–Việt |
|---|---|---|
| vedettes | 45 987 | 119 091 |
| sens | 79 303 | 190 621 |
| — avec exemple traduit | **34 %** | **9 %** |
| exemples | 45 995 | 27 401 |
| formes fléchies | 240 137 | 199 656 |
| pages de forme ambiguë | 10 355 | 23 052 |
| clés | 280 436 | 295 898 |
| bundle | 55,6 Mo | 53,1 Mo |

Les 9 % d'exemples côté anglais sont la faiblesse connue de ce dictionnaire, et
elle vient de la source : le Wiktionnaire vietnamien documente bien mieux le
français que l'anglais. Rien dans le pipeline ne peut la combler ; seule une
autre source le pourrait.

Ce qui reste : `make sync`, la boucle qui ramène une correction faite sur le
site jusque dans les bundles.

## Faire tourner

```bash
make fetch                 # les sources, et data/sources.lock qui dit lesquelles
make install               # → Pháp-Việt.dictionary
make install LANG=en       # → Anh-Việt.dictionary
make both                  # les deux
make install TOP=3000      # une coupe, pour essayer
```

Puis, **une seule fois par dictionnaire** : Dictionary.app > Réglages > cochez-le,
et remontez-le au-dessus des dictionnaires d'Apple. Rien ne le consultera avant.

Sur Apple Silicon, les binaires du DDK sont x86_64 :
`softwareupdate --install-rosetta --agree-to-license`.

```bash
make check LANG=en    # la clé est-elle dans le XML, et mène-t-elle au bon mot ?
make verify LANG=en   # le bundle installé sait-il y répondre ?  ← celui qui compte
```

## Le site

Le second shell. Le même `lexicon-LL.jsonl` sort en NDJSON, et c'est *practice*
qui l'ingère avec son pilote et ses identifiants — le dictionnaire décide du
contenu, l'application décide de sa base.

```bash
make mongo LANG=fr           # → build/mongo-fr.ndjson
cd ../practice && node --env-file .env \
  packages/server/src/scripts/seedLexicon.ts ../dictionnaire/build/mongo-fr.ndjson
```

Le chargement est idempotent : il remplace une langue au lieu d'y ajouter, et
pose les index sans lesquels chaque recherche balaierait 165 000 documents.
`--keep-ids` met à jour au lieu de recharger, ce qui préserve les `_id` — donc
l'historique et les favoris — au prix de la vitesse.

Deux collections. `dictionary` garde la forme que practice lisait déjà, parce
que l'historique et les favoris pointent ses `_id` : on la remplit, on ne la
refait pas. `dictionary_forms` est nouvelle, et c'est elle qui manquait au
site — « allions » n'y donnait rien alors que le bundle le résout depuis
Verbiste.

## Les sources

Un dictionnaire, ici, c'est **du sens** et **de la morphologie**, et les deux ne
viennent jamais du même endroit.

### Le sens

| | Source | Licence |
|---|---|---|
| fr | [Wiktionnaire vietnamien](https://vi.wiktionary.org), section « Tiếng Pháp », extrait par [kaikki.org](https://kaikki.org/viwiktionary/) | CC BY-SA 4.0 |
| en | idem, section « Tiếng Anh » | CC BY-SA 4.0 |

Des vedettes françaises et anglaises **glosées en vietnamien**, écrites par des
humains, déjà en JSON. C'est tout l'intérêt de cette édition-là du Wiktionnaire.

### La morphologie

kaikki n'en donne pas : **600 formes fléchies** dans le dump français, **8 014**
dans l'anglais pour 119 166 vedettes. Chaque langue a donc son module, et c'est
le seul endroit où les deux dictionnaires diffèrent vraiment.

| | Source | Ce qu'elle donne |
|---|---|---|
| fr | [Verbiste](http://sarrazip.com/dev/verbiste.html) | 146 modèles qui **engendrent** le paradigme complet de 7 011 verbes |
| fr | [Lexique 3.83](http://www.lexique.org) | les pluriels, les féminins, et la fréquence |
| en | exceptions de **WordNet 3.0** | 5 940 irréguliers, à la main |
| en | **des règles** | pluriels, `-s`, `-ing`, `-ed`, `-er`, `-est` |
| en | [FrequencyWords](https://github.com/hermitdave/FrequencyWords) | la fréquence |

### La même leçon, deux fois

Les deux langues ont d'abord eu une base d'occurrences, et les deux l'ont perdue
pour la même raison.

**Lexique**, français, n'atteste que ce que ses corpus contiennent : **10,1
formes par verbe** là où un paradigme en compte ~45, 56 % des verbes sous les
dix formes, huit verbes complets sur 6 399. « allions » y figure sous *aller* et
nulle part sous *allier*. Verbiste, génératif, les a toutes.

**UniMorph**, anglais, a l'air plus gros — 189 780 formes contre 5 940 — et rate
« children », « was », « were », « feet », « geese », en rangeant « ran » sous
*rin*, un verbe dialectal rare. Les listes de WordNet, mille fois plus petites
et faites à la main, ont tout bon.

Deux fois la même conclusion : **le volume ne dit rien de la justesse**, et un
dictionnaire qu'on interroge en tapant la forme qu'on vient de lire a besoin de
paradigmes engendrés, pas de fréquences observées.

Côté anglais, les règles engendrent, et WordNet **tait** la règle là où il a
rempli la case : sans ça on écrivait « goed » à côté de « went ». Le
redoublement de consonne ne s'applique qu'aux monosyllabes — « stop » →
« stopped » se décide sur l'accent tonique, que rien ici ne connaît, et
« visitted » serait une clé fausse.

## base ⊕ edits

Un bundle `.dictionary` est compilé et en lecture seule : il n'existe pas de
mise à jour incrémentale. Toute correction veut dire recompiler. D'où le
découpage :

```
data/sources/     retéléchargeable, jamais dans git, épinglé par sources.lock
data/edits-fr.jsonl  vos corrections, dans git, une ligne par entrée touchée
build/lexicon-LL.jsonl base ⊕ edits — ce que lisent les deux émetteurs
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
