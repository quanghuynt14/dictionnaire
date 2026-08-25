#!/bin/sh
#
# Installe les dictionnaires Pháp–Việt et Anh–Việt sur ce Mac.
#
#   curl -fsSL https://raw.githubusercontent.com/quanghuynt14/dictionnaire/HEAD/scripts/install.sh | sh
#
# ou, si les .zip sont déjà là :
#
#   sh install.sh                 les .zip posés à côté
#   sh install.sh ~/Downloads     les .zip d'un autre dossier
#
# Rien à compiler : un bundle .dictionary est un dossier de données, pas un
# programme. Ni Python, ni le DDK, ni Rosetta, ni les 190 Mo de sources — ceux-là
# ne servent qu'à *fabriquer* le dictionnaire, jamais à s'en servir.
#
# /bin/sh et non bash : ce script est fait pour être tubé dans un shell qu'on
# ne choisit pas.

set -eu

REPO="quanghuynt14/dictionnaire"
DEST="$HOME/Library/Dictionaries"
SOURCE_DIR="${1:-}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT INT TERM

# --- où sont les archives ---------------------------------------------------

if [ -z "$SOURCE_DIR" ]; then
  # Tubé depuis curl : $0 ne désigne aucun dossier utile, il faut aller
  # chercher les archives. Sinon, on regarde à côté du script.
  case "${0:-}" in
    */*) here="$(cd "$(dirname "$0")" && pwd)" ;;
    *)   here="" ;;
  esac
  # On ne cherche que **ses** archives, pas n'importe quel *.dictionary.zip :
  # un install.sh posé dans ~/Downloads à côté de l'archive d'un autre
  # dictionnaire installerait celui-là, sans rien dire. Constaté pour de bon.
  if [ -n "$here" ] && [ -f "$here/phap-viet.dictionary.zip" ]; then
    SOURCE_DIR="$here"
  fi
fi

if [ -z "$SOURCE_DIR" ]; then
  SOURCE_DIR="$tmp/dl"
  mkdir -p "$SOURCE_DIR"
  echo "  Téléchargement de la dernière version…"

  # Noms ASCII : GitHub remplace tout caractère non-ASCII du nom d'un fichier
  # de version par un point — « Pháp-Việt.dictionary.zip » y est stocké
  # « Phap-Vi.t.dictionary.zip » — et l'URL accentuée rend alors 404.
  for slug in phap-viet anh-viet; do
    echo "    ↓ $slug"
    if ! curl -fsSL -o "$SOURCE_DIR/$slug.dictionary.zip" \
        "https://github.com/$REPO/releases/latest/download/$slug.dictionary.zip"; then
      cat >&2 <<ERR

  Téléchargement impossible : $slug.dictionary.zip

  Vérifiez la connexion, ou prenez les archives à la main sur
  https://github.com/$REPO/releases/latest puis relancez :

      sh install.sh ~/Downloads

ERR
      exit 1
    fi
  done
fi

# --- installation -----------------------------------------------------------

found=0
mkdir -p "$DEST"

for zip in "$SOURCE_DIR"/*.dictionary.zip; do
  [ -e "$zip" ] || continue
  found=1
  rm -rf "$tmp/x"
  mkdir -p "$tmp/x"
  ditto -x -k "$zip" "$tmp/x"

  # Le nom d'installation vient du bundle **dans** l'archive, jamais du nom du
  # fichier : l'archive s'appelle « phap-viet » en ASCII pour survivre à
  # GitHub, le dictionnaire s'appelle « Pháp-Việt » et doit le rester.
  bundle="$(find "$tmp/x" -maxdepth 2 -name '*.dictionary' -print -quit)"
  [ -d "$bundle" ] || { echo "  ✗ pas de bundle dans $(basename "$zip")" >&2; continue; }
  name="$(basename "$bundle")"
  echo "  → $name"

  # Un fichier téléchargé porte l'attribut de quarantaine. Dictionary.app lit
  # quand même — ce ne sont pas des exécutables — mais l'enlever évite une
  # question à laquelle personne ne saura répondre.
  xattr -dr com.apple.quarantine "$bundle" 2>/dev/null || true

  # `rm -rf` avant `ditto`, et ce n'est pas une précaution de style : copier
  # par-dessus un bundle déjà en place laisse macOS avec un index périmé. Le
  # dictionnaire continue de répondre à l'API et disparaît de la fenêtre de
  # consultation — la panne qui a coûté trois fausses pistes dans conjugaison.
  rm -rf "$DEST/$name"
  ditto --noextattr --norsrc "$bundle" "$DEST/$name"
done

if [ "$found" -eq 0 ]; then
  echo "Aucun *.dictionary.zip dans $SOURCE_DIR" >&2
  exit 1
fi

touch "$DEST"

# `killall LookupViewService` ne marche pas : ce sont des services XPC, killall
# ne les reconnaît pas et sort sans rien dire. Il en tourne un par application
# hôte, chacun gardant la liste des dictionnaires pour toute sa durée de vie.
pkill -9 -f LookupViewService >/dev/null 2>&1 || true
pkill -9 -f DictionaryServiceHelper >/dev/null 2>&1 || true
killall cfprefsd >/dev/null 2>&1 || true

cat <<'MSG'

  Installé dans ~/Library/Dictionaries.

  Il reste une chose, et aucun script ne peut la faire à votre place :
  ouvrez Dictionnaire.app > Réglages, cochez « Pháp–Việt » et « Anh–Việt »,
  puis remontez-les au-dessus des dictionnaires d'Apple.

  Ensuite, ⌃⌘D sur n'importe quel mot, n'importe où.
MSG
