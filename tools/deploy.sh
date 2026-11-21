#!/usr/bin/env bash
# Publie site/ sur AlwaysData via rsync/SSH.
# Les paramètres sont lus dans .deploy.env (non versionné), par exemple :
#   ALWAYSDATA_SSH=moncompte@ssh-moncompte.alwaysdata.net
#   ALWAYSDATA_PATH=www/lectures/
set -euo pipefail
cd "$(dirname "$0")/.."
source .deploy.env
.venv/bin/python tools/build.py
rsync -avz --delete --dry-run site/ "$ALWAYSDATA_SSH:$ALWAYSDATA_PATH"
read -r -p "Publier pour de bon ? [o/N] " ok
[[ "$ok" == "o" ]] && rsync -avz --delete site/ "$ALWAYSDATA_SSH:$ALWAYSDATA_PATH"
