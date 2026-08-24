# Deux dictionnaires, un seul code. `make install` bâtit le français,
# `make install LANG=en` l'anglais, `make both` les deux.
LANG               ?= fr
TOP                ?= all

DICT_NAME           = $(shell python3 -c "import sys;sys.path.insert(0,'scripts');import sources;print(sources.lang('$(LANG)')['bundle'])")
DICT_SRC_PATH       = src/$(LANG).xml
CSS_PATH            = src/entry.css
PLIST_PATH          = src/Info-$(LANG).plist

DDK_DIR             = tools/dictionary-development-kit
DDK_BIN             = $(DDK_DIR)/bin
DDK_REPO            = https://github.com/SebastianSzturo/Dictionary-Development-Kit.git

DICT_DEV_KIT_OBJ_DIR = ./objects
export DICT_DEV_KIT_OBJ_DIR

DESTINATION_FOLDER  = $(HOME)/Library/Dictionaries

.PHONY: all both fetch normalize xml mongo build install uninstall setup clean check verify refresh dist release

all: install

both:
	@$(MAKE) --no-print-directory install LANG=fr
	@$(MAKE) --no-print-directory install LANG=en

# Les outils de compilation d'Apple sont x86_64 : sur Apple Silicon il faut
#   softwareupdate --install-rosetta --agree-to-license
setup:
	@test -d $(DDK_DIR) || git clone --depth 1 $(DDK_REPO) $(DDK_DIR)
	@chmod +x $(DDK_BIN)/* 2>/dev/null || true

fetch:
	python3 scripts/fetch.py

normalize:
	@python3 scripts/normalize.py --lang $(LANG) $(if $(filter all,$(TOP)),--all,--top $(TOP))

xml: normalize
	python3 scripts/emit_apple.py --lang $(LANG)

# L'autre shell : le même lexique, en NDJSON, pour la base de practice.
mongo: normalize
	python3 scripts/emit_mongo.py --lang $(LANG)

# -v 10.11 : la disposition moderne du bundle — données sous Contents/Resources,
# index trie, IDXDictionaryVersion 3. Sans elle, build_dict.sh vise 10.5 par
# défaut et écrit un bundle que les macOS récents ne lisent plus.
#
# preserve_unused_ref_id_in_reference_index : par défaut le DDK ne met dans
# l'index de référence que les entrées *citées* par un lien ou par le front
# matter. Nous n'avons ni l'un ni l'autre, donc cet index sort vide — et la
# fenêtre de consultation, qui résout l'entrée par son identifiant, retombe
# alors sur la première du fichier quelle que soit la recherche.
#
# Le DDK signale l'index vide et continue. On en fait une erreur : c'est une
# panne invisible partout sauf dans une fenêtre qu'aucun script n'ouvre.
build: setup xml
	@preserve_unused_ref_id_in_reference_index=1 \
		"$(DDK_BIN)/build_dict.sh" -v 10.11 $(DICT_NAME) $(DICT_SRC_PATH) \
		$(CSS_PATH) $(PLIST_PATH) 2>&1 | tee $(DICT_DEV_KIT_OBJ_DIR)-build.log
	@# build_dict.sh sort en 0 même quand il s'arrête, et `| tee` masquerait
	@# de toute façon son code. On lit donc le log : c'est là qu'est la vérité.
	@if grep -qE "^Error\.|parser error" $(DICT_DEV_KIT_OBJ_DIR)-build.log; then \
		echo; \
		echo "ERREUR : le DDK s'est arrêté — voir le log ci-dessus."; \
		exit 1; \
	fi
	@if grep -q "No reference index record" $(DICT_DEV_KIT_OBJ_DIR)-build.log; then \
		echo; \
		echo "ERREUR : index de référence vide. La fenêtre de consultation"; \
		echo "affichera la première entrée du fichier pour toute recherche."; \
		exit 1; \
	fi

# Le `rm -rf` n'est pas une précaution de style. `ditto` par-dessus un bundle
# déjà en place laisse macOS avec un index périmé : le dictionnaire continue de
# répondre à l'API et disparaît de la fenêtre de consultation. Dans conjugaison
# ça a coûté trois fausses pistes — plist, langue, index de référence — alors
# que réinstaller proprement suffisait.
# Le test avant le `rm -rf` n'est pas de la ceinture-bretelle. Le jour où le
# plist engendré portait un « -- » dans un commentaire, le DDK s'est arrêté,
# make a continué, et la cible a effacé le dictionnaire installé avant de
# découvrir qu'elle n'avait rien à mettre à la place. On se retrouve alors sans
# dictionnaire du tout — pire que l'ancien.
install: build
	@test -d "$(DICT_DEV_KIT_OBJ_DIR)/$(DICT_NAME).dictionary" || { \
		echo "ERREUR : $(DICT_NAME).dictionary n'a pas été construit."; \
		echo "Rien n'a été désinstallé."; \
		exit 1; }
	mkdir -p $(DESTINATION_FOLDER)
	rm -rf "$(DESTINATION_FOLDER)/$(DICT_NAME).dictionary"
	ditto --noextattr --norsrc \
		"$(DICT_DEV_KIT_OBJ_DIR)/$(DICT_NAME).dictionary" \
		"$(DESTINATION_FOLDER)/$(DICT_NAME).dictionary"
	touch $(DESTINATION_FOLDER)
	@$(MAKE) --no-print-directory refresh
	@echo
	@echo "Installé. Relancez Dictionary.app, puis Réglages > Sources et cochez"
	@echo "« $(DICT_NAME) »."

# `killall LookupViewService` ne marche pas : ce sont des services XPC, killall
# ne les reconnaît pas et sort sans rien dire. Il y en a un par application
# hôte, chacun garde la liste des dictionnaires pour toute sa durée de vie.
# Dans conjugaison ça a fait croire pendant une séance entière que les
# corrections n'avaient aucun effet.
refresh:
	@pkill -9 -f LookupViewService 2>/dev/null || true
	@pkill -9 -f DictionaryServiceHelper 2>/dev/null || true
	@killall cfprefsd 2>/dev/null || true
	@echo "Services de consultation relancés."

uninstall:
	rm -rf "$(DESTINATION_FOLDER)/$(DICT_NAME).dictionary"

# check  : la clé est-elle dans le XML, et mène-t-elle au bon mot ?
# verify : le bundle installé sait-il y répondre ? C'est celui qui compte.
check:
	python3 scripts/check.py --lang $(LANG)

verify:
	python3 scripts/verify_lookup.py --lang $(LANG)

# --- distribution ---------------------------------------------------------
#
# Un bundle .dictionary est un dossier de données : il se copie d'un Mac à
# l'autre tel quel. Rien à compiler en face — le DDK, Python et les 190 Mo de
# sources ne servent qu'à le *fabriquer*.
#
# `ditto -c -k` plutôt que `zip` : c'est l'outil d'Apple, il préserve ce qu'un
# bundle attend, et c'est le pendant exact du `ditto -x -k` de install.sh.
DIST = dist

dist:
	@mkdir -p $(DIST)
	@for lang in fr en; do \
		name=$$(python3 -c "import sys;sys.path.insert(0,'scripts');import sources;print(sources.lang('$$lang')['bundle'])"); \
		slug=$$(python3 -c "import sys;sys.path.insert(0,'scripts');import sources;print(sources.lang('$$lang')['slug'])"); \
		src="$(DESTINATION_FOLDER)/$$name.dictionary"; \
		test -d "$$src" || { echo "✗ $$name.dictionary pas installé — lancez make install LANG=$$lang"; exit 1; }; \
		rm -f "$(DIST)/$$slug.dictionary.zip"; \
		ditto -c -k --sequesterRsrc --keepParent "$$src" "$(DIST)/$$slug.dictionary.zip"; \
		printf "  %-22s %5.1f Mo\n" "$$slug.dictionary.zip" $$(echo "$$(stat -f %z "$(DIST)/$$slug.dictionary.zip")/1000000" | bc -l); \
	done
	@cp scripts/install.sh $(DIST)/
	@echo "  → $(DIST)/  (les .zip et install.sh — copiez le dossier sur l'autre Mac)"

# Une version sur GitHub, pour ne pas passer par une clé USB. Le dépôt est
# privé : `gh release download` sur l'autre Mac demande d'y être authentifié.
release: dist
	@v=$$(date +%Y.%m.%d); \
	gh release create "v$$v" $(DIST)/*.zip $(DIST)/install.sh \
		--title "Dictionnaires $$v" \
		--notes "Pháp–Việt et Anh–Việt pour Dictionary.app.$$(printf '\n\n')Sur l'autre Mac :$$(printf '\n')\`\`\`$$(printf '\n')gh release download v$$v --repo quanghuynt14/dictionnaire --dir ~/Downloads/dicos$$(printf '\n')bash ~/Downloads/dicos/install.sh$$(printf '\n')\`\`\`" \
		|| gh release upload "v$$v" $(DIST)/*.zip $(DIST)/install.sh --clobber

clean:
	rm -rf $(DICT_DEV_KIT_OBJ_DIR) $(DICT_DEV_KIT_OBJ_DIR)-build.log build dist src/*.xml
