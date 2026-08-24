#!/bin/bash
#
# Installe les dictionnaires Pháp–Việt et Anh–Việt sur ce Mac.
#
#   ./install.sh                  les .zip posés à côté de ce script
#   ./install.sh ~/Downloads      les .zip d'un autre dossier
#
# Rien à compiler : un bundle .dictionary est un dossier de données, pas un
# programme. Ni Python, ni le DDK, ni Rosetta, ni les 190 Mo de sources — ceux-là
# ne servent qu'à *fabriquer* le dictionnaire, jamais à s'en servir.

set -euo pipefail

SOURCE_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
DEST="$HOME/Library/Dictionaries"

shopt -s nullglob
zips=("$SOURCE_DIR"/*.dictionary.zip)
if [ ${#zips[@]} -eq 0 ]; then
  echo "Aucun *.dictionary.zip dans $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$DEST"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for zip in "${zips[@]}"; do
  name="$(basename "$zip" .zip)"
  echo "  → $name"

  rm -rf "${tmp:?}/x" && mkdir -p "$tmp/x"
  ditto -x -k "$zip" "$tmp/x"

  bundle="$tmp/x/$name"
  [ -d "$bundle" ] || bundle="$(find "$tmp/x" -maxdepth 2 -name '*.dictionary' -print -quit)"
  if [ ! -d "$bundle" ]; then
    echo "     ✗ pas de bundle .dictionary dans l'archive" >&2
    continue
  fi

  # Un fichier téléchargé porte l'attribut de quarantaine. Dictionary.app lit
  # quand même — ce ne sont pas des exécutables — mais l'enlever évite une
  # question à laquelle personne ne saura répondre.
  xattr -dr com.apple.quarantine "$bundle" 2>/dev/null || true

  # `rm -rf` avant `ditto`, et ce n'est pas une précaution de style : copier
  # par-dessus un bundle déjà en place laisse macOS avec un index périmé. Le
  # dictionnaire continue de répondre à l'API et disparaît de la fenêtre de
  # consultation — une panne qui a coûté trois fausses pistes dans conjugaison.
  rm -rf "$DEST/$name"
  ditto --noextattr --norsrc "$bundle" "$DEST/$name"
done

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
