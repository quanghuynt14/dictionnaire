# dictionnaire

Deux dictionnaires **vers le vietnamien** — français et anglais — pour
Dictionary.app, et pour le web.

Ils ne demandent rien à personne au moment où on les consulte : pas de modèle
de langue, pas de requête réseau, pas de clé d'API. Le contenu est écrit par
des humains, compilé une fois, et lu depuis le disque.

## Installer

```bash
curl -fsSL https://raw.githubusercontent.com/quanghuynt14/dictionnaire/HEAD/scripts/install.sh | sh
```

Trente-quatre mégaoctets, une dizaine de secondes. Rien à compiler : un bundle
`.dictionary` est un dossier de **données**, pas un programme — ni Python, ni le
DDK, ni Rosetta, ni les 190 Mo de sources, qui ne servent qu'à le *fabriquer*.

Il reste **une chose, à faire une seule fois**, et qu'aucun script ne peut faire
à votre place : ouvrez Dictionnaire.app > Réglages, cochez « Pháp–Việt » et
« Anh–Việt », et remontez-les au-dessus des dictionnaires d'Apple. Rien ne les
consultera avant.

Ensuite, ⌃⌘D sur n'importe quel mot, n'importe où dans macOS.

<details>
<summary>Sans le tube, ou hors ligne</summary>

Le même script accepte un dossier d'archives — celles de la
[dernière version](https://github.com/quanghuynt14/dictionnaire/releases/latest),
ou celles que `make dist` fabrique ici :

```bash
sh install.sh                 # les .zip posés à côté
sh install.sh ~/Downloads     # ou dans le dossier indiqué
```

Posé à côté, il ne cherche que **ses** archives, par leur nom. Il cherchait
n'importe quel `*.dictionary.zip`, et rangé dans un dossier qui en contenait
un autre il installait celui-là en annonçant une réussite. Un dossier passé en
argument garde l'ancien comportement : là, c'est un choix explicite.

Il refait les deux gestes qui comptent, et pour lesquels il y a des raisons
écrites dans son en-tête : `rm -rf` avant `ditto`, sinon macOS garde un index
périmé et le dictionnaire disparaît de la fenêtre de consultation ; et un
`pkill -f` sur les services XPC de consultation, que `killall` ne reconnaît
pas. Il enlève aussi la quarantaine d'un fichier téléchargé.

</details>

### À côté

[**conjugaison**](https://github.com/quanghuynt14/conjugaison) donne la
*forme* — 2 004 verbes, 77 277 formes, une conjugaison inversée. Les deux
s'installent côte à côte : `allions` ouvre sa traduction ici, sa conjugaison
là. C'est pourquoi les pages de verbe de ce dictionnaire renvoient à
« Conjugaison française » au lieu de recopier quarante-cinq cases.

## Ce qu'ils savent faire

Chercher la forme qu'on vient de lire, pas seulement la vedette.

```
allions   →  aller     imparfait de l'indicatif, 1ʳᵉ pers. plur.
          →  allier    présent de l'indicatif, 1ʳᵉ pers. plur.
prises    →  prendre, pris, prise, priser
went      →  go
saw       →  see
```

Une forme qui mène à plusieurs mots ouvre **une page qui les porte tous** : la
fenêtre de survol ne rend qu'une entrée par dictionnaire, et n'en montrer qu'un
serait une demi-réponse. Chaque mot renvoie à l'article du Wiktionnaire dont il
sort, pour vérifier une glose.

## État

**Phase 0 terminée**, sur tout le dump, dans les deux langues.

| | Pháp–Việt | Anh–Việt |
|---|---|---|
| vedettes | 46 160 | 119 108 |
| sens | 79 607 | 190 647 |
| — avec exemple traduit | **34 %** | **9 %** |
| exemples | 45 995 | 27 401 |
| formes fléchies | 240 788 | 199 674 |
| pages de forme ambiguë | 10 488 | 23 056 |
| clés | 281 174 | 295 929 |
| bundle | 55,6 Mo | 53,1 Mo |

Les 9 % d'exemples côté anglais sont la faiblesse connue de ce dictionnaire, et
elle vient de la source : le Wiktionnaire vietnamien documente bien mieux le
français que l'anglais. Rien dans le pipeline ne peut la combler ; seule une
autre source le pourrait.

Ce qui reste : `make sync`, la boucle qui ramène une correction faite sur le
site jusque dans les bundles.

### Việt–Pháp, le sens inverse

Un troisième dictionnaire, encore à l'essai : des mots vietnamiens, expliqués
en français. `make mongo LANG=vi` le construit ; il tient en vingt secondes et
500 Mo, sans morphologie à engendrer.

Il lit deux Wiktionnaires, dans cet ordre :

1. **le français**, section « Vietnamien » — la langue du dictionnaire ;
2. **l'anglais**, section « Vietnamese », affiché tel quel et marqué EN. Il
   connaît deux fois plus de mots vietnamiens, et ses sens sont souvent plus
   actuels : « tham nhũng » y est « to be corrupt », là où le français dit
   « Tracassier et cupide ».

L'anglais n'est pas traduit en français. Une traduction automatique ne serait
écrite par personne, et personne ne pourrait la corriger sur un wiki.

| | Việt–Pháp |
|---|---|
| vedettes | 32 717 |
| — en français seulement | 4 470 |
| — en anglais seulement | 18 616 |
| — dans les deux | 9 631 |
| sens | 61 788 |
| — avec exemple traduit | **31 %** |
| clés tapées (sans accents, autre place du ton, renvois) | 28 165 |
| pages de forme ambiguë | 2 587 |

Ce que le pipeline fait propre à cette langue (`morph_vi.py`) :

- **sans accents** : « an » mène à ăn, án, ấn, ẩn, ân…, les plus fréquents
  d'abord ;
- **la place du ton** : « hoà » et « hòa » sont une seule page. 485 mots
  étaient coupés en deux, un par Wiktionnaire ;
- **les renvois** : « siễn » mène à « suyễn ». La phrase « alternative form
  of » n'est pas affichée.

Les sinogrammes ne sont pas repris : ils décrivent l'écriture chinoise, pas
un mot qu'on lit en quốc ngữ.

#### Les mille entrées reindoo

Pour les 1 000 mots vietnamiens les plus fréquents, une entrée écrite pour
un francophone passe **avant** les sens du Wiktionnaire. Elle donne des
équivalents français, un sens par différence à apprendre, des étiquettes
([familier], [Nord], [clf: con]…), des exemples traduits et une note sur
l'erreur qu'un francophone fait. Les sens du Wiktionnaire suivent, tels quels.

Ces entrées ne sont pas du Wiktionnaire. Claude Opus les a rédigées à partir
des deux Wiktionnaires et de vraies phrases (sous-titres, TED, Tatoeba). Un
second Opus les a ensuite relues. Aucun humain ne les a encore relues.

- `data/reindoo-vi.jsonl` : les entrées, une par ligne ;
- `scripts/import_reindoo.py` : le fichier vient du `entries.md` de l'étude ;
- `emit_mongo.py` les place en tête, avec `"source": "reindoo"` et la note
  dans `note`. Leur ligne courte (`translated`) remplace celle du
  Wiktionnaire.

Sur 4 922 exemples, 2 450 sont de vraies phrases, reprises ou raccourcies. Leur
source, dans le corpus aligné français–vietnamien d'[OPUS](https://opus.nlpl.eu) :

| Source | Exemples | Licence |
|---|---|---|
| [OpenSubtitles](https://www.opensubtitles.org), via OPUS (Lison et Tiedemann, 2016) | 1 408 | sous-titres d'utilisateurs ; OPUS les redistribue sans licence propre |
| [TED](https://www.ted.com) : NeuLab-TedTalks et TED2020 | 1 038 | [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/) |
| [Tatoeba](https://tatoeba.org) | 4 | [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/) |

Les autres exemples sont écrits pour l'entrée. Aucun ne vient de QED : sa
licence le réserve à la recherche. `drop_qed.py`, dans l'étude, les retire
avant l'import.

### Trung–Việt, pour le chinois

Un quatrième, à l'essai aussi : des mots chinois (mandarin), expliqués en
vietnamien. Il nourrit « Reindoo Hán ». Même méthode que Việt–Pháp :

1. **le Wiktionnaire vietnamien**, sections « Tiếng Quan Thoại » et « Tiếng
   Trung Quốc » — la langue du dictionnaire, 7 000 mots environ ;
2. **le Wiktionnaire anglais**, section « Chinese », affiché tel quel et
   marqué EN.

```bash
python3 scripts/fetch.py --lang zh             # les sources de zh seulement
python3 scripts/fetch.py --lang zh --limit 30000   # un échantillon, pour un petit disque
make mongo LANG=zh                              # → build/mongo-zh.ndjson
```

Le dump anglais pèse 1,2 Go. `fetch.py` le filtre pendant qu'il arrive
(`morph_zh.slim`) : le mandarin seulement, et les champs qu'on lit. Il ne
touche jamais le disque en entier. `fetch.py` sans `--lang` ne le télécharge
pas ; la CI le construit en entier (`.github/workflows/zh.yml`).

Ce que le pipeline fait propre à cette langue (`morph_zh.py`) :

- **une entrée par mot**, sous la forme simplifiée : « 學 » et « 学 » sont une
  page. Le lien vient du wiki (la page simplifiée renvoie à la traditionnelle) ;
  OpenCC ne sert qu'à choisir laquelle afficher. L'autre graphie mène à la
  page ;
- **le pinyin** remplit `ipa`. On le cherche avec ou sans tons, collé ou en
  syllabes, ou les tons en chiffres : « zhōngguó », « zhongguo », « zhong
  guo », « zhong1guo2 » mènent à 中国 ;
- **la lecture Hán Việt** (`hanviet`) : « học » pour 学, « Trung Quốc » pour
  中国. Elle vient de la section vietnamienne du Wiktionnaire anglais. Un mot
  sans lecture notée se compose caractère par caractère, si chacun n'en a
  qu'une ;
- **le mandarin seulement** : un sens marqué cantonais, hokkien, wu… est
  écarté.

Champs en plus dans `mongo-zh.ndjson`, ignorés par qui ne les lit pas :
`hanviet`, `traditional`, `variants`, et `pinyin` sur chaque exemple.

## Reconstruire depuis les sources

Rien de tout ça n'est nécessaire pour *se servir* du dictionnaire — seulement
pour le refaire, ou pour le modifier.

```bash
make fetch                 # les sources, et data/sources.lock qui dit lesquelles
make install               # → Pháp-Việt.dictionary
make install LANG=en       # → Anh-Việt.dictionary
make both                  # les deux
make install TOP=3000      # une coupe, pour essayer
```

Sur Apple Silicon, les binaires du DDK sont x86_64 :
`softwareupdate --install-rosetta --agree-to-license`.

```bash
make check LANG=en    # la clé est-elle dans le XML, et mène-t-elle au bon mot ?
make verify LANG=en   # le bundle installé sait-il y répondre ?  ← celui qui compte
```

## Fabriquer les archives

```bash
make dist        # → dist/ : les deux .zip en ASCII, et install.sh
make release     # publie une version datée sur GitHub
```

Les archives portent un slug ASCII — `phap-viet`, `anh-viet` — et non le nom
du bundle : GitHub remplace tout caractère non-ASCII du nom d'un fichier de
version par un point, et « Pháp-Việt.dictionary.zip » y devient
« Phap-Vi.t.dictionary.zip », dont l'URL rend 404. L'installateur lit donc le
nom du dictionnaire *dans* l'archive.

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
| zh | idem, sections « Tiếng Quan Thoại » et « Tiếng Trung Quốc » ; puis le [Wiktionary anglais](https://en.wiktionary.org), section « Chinese » (et « Vietnamese » pour les lectures Hán Việt) | CC BY-SA 4.0 |
| zh | [FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles, zh_cn) pour le rang | CC BY-SA 4.0 |
| zh | [OpenCC](https://github.com/BYVoid/OpenCC), table traditionnel → simplifié | Apache 2.0 |

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

### Les vedettes que wiktextract ne voit pas

kaikki lit les définitions écrites en syntaxe MediaWiki — les lignes qui
commencent par `#`. Une partie du Wiktionnaire vietnamien ne les écrit pas
ainsi. L'import du *Free Vietnamese Dictionary Project* (`{{R:FVDP}}`) a posé
des `<LI class=def>` en HTML brut, et d'autres pages mettent la définition sur
une ligne indentée après un tiret. wiktextract n'y voit aucune glose et rend un
sens vide.

`normalize.py` écarte une entrée sans glose — à raison. Mais ces pages-là ne
sont pas vides : elles sont mal balisées. Mesuré, **197 vedettes françaises
(0,43 %) et 75 anglaises (0,06 %)**, dont « mélancolie », « dictionnaire »,
« Asie », « français ».

`scripts/rescue.py` relit leur wikitexte par l'API MediaWiki, quarante titres
par requête, et en tire les gloses selon quatre formes rencontrées. **173 des
197 françaises et 17 des 75 anglaises** rentrent ainsi.

Ce qui reste dehors le mérite : « cocagne » n'a réellement que des exemples et
aucune définition, et la page « appogiature » a été vandalisée — son titre de
section est une obscénité vietnamienne, et il n'y a pas de définition dessous.

Une règle en est sortie, et elle vaut au-delà de ce script : **une glose fausse
est pire qu'une glose absente**. Le repli par puces rendait « IMNSHO, IMAO »
comme sens de « IMHO » — c'étaient ses synonymes. Les puces ne sont donc lues
que dans un bloc dont on sait qu'il porte une définition, alors qu'un `#`, qui
n'est jamais une liste de synonymes, se lit partout.

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
