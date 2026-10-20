#!/usr/bin/env bash
# Installiert die Werkzeugkette von site-anatomy isoliert nach ~/.local/share/site-anatomy.
# NUR nach des Nutzers ausdruecklicher Freigabe ausfuehren (Regel: keine fremden Pakete ohne Ja).
# playwright 1.61.1 nutzt das vorhandene chromium-1228 in ~/.cache/ms-playwright, laedt also keinen Browser.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${SITE_ANATOMY_HOME:-$HOME/.local/share/site-anatomy}"
mkdir -p "$ROOT"
cp "$HERE/package.json" "$HERE/package-lock.json" "$ROOT/"
cd "$ROOT"
# npm ci: installiert exakt den Lockfile-Stand (auch transitiv), statt Bereiche neu aufzuloesen.
# --ignore-scripts: keine Install-Skripte fremder Pakete. sharp bringt vorkompilierte Binaries
# ueber optionale @img/*-Pakete mit und braucht dafuer kein Skript.
# @axe-core/playwright verlangt Node >=22.12; netcup laeuft seit 2026-10-20 auf Node 24.22.0 (nodesource node_24.x).
npm ci --ignore-scripts --no-audit --no-fund
npm ls --depth=0
node -e "const s=require('$ROOT/node_modules/sharp'); console.log('sharp ok', s.versions.sharp)"
test -d "$HOME/.cache/ms-playwright/chromium_headless_shell-1228" && echo "chromium 1228 vorhanden" || echo "WARNUNG: chromium 1228 fehlt"
echo "Installiert nach $ROOT"
