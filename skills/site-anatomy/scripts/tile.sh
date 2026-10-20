#!/usr/bin/env bash
# site-anatomy, nach measure.mjs: Screenshots kacheln und Kontaktboegen bauen, damit Claude sie lesen kann.
# Aufruf: bash tile.sh <arbeitsordner>   (der Arbeitsordner selbst, nicht .../shots)
# Liest kopien/shots/**.png und kopien/images/*, schreibt kopien/tiles/ und kopien/sheets/.
# Je Bogen sheet_NN.png plus sheet_NN.txt (Zeile, Spalte, Dateiname) fuer den Abgleich mit images.json.
# Was ffmpeg 4.4 nicht dekodiert (AVIF, SVG), wandelt sharp aus der Werkzeugkette nach PNG.
# Exit 0 ok, 3 kein gueltiger Arbeitsordner, 4 ffmpeg fehlt.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR_IN="${1:?Aufruf: tile.sh <arbeitsordner>}"
MAX_W=1280   # breiter wird von der Vision-Analyse ohnehin herunterskaliert
MAX_H=2000   # gemessen: 12.000 px hohe Bilder kommen sonst auf 2.000 px verkleinert an
THUMB=320    # 4x5 Thumbnails ergeben einen Bogen von 1280x1600
COLS=4
ROWS=5
SHARP_MAX=640  # Zwischen-PNG aus sharp; doppelte Thumbnail-Breite reicht fuer saubere Verkleinerung
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo "ffmpeg/ffprobe fehlt" >&2; exit 4; }

# Arbeitsordner-Pruefung an einer Stelle (workdir.py): realpath unter ~/site-anatomy, LOESCHDATUM vorhanden
DIR="$(python3 -I "$HERE/workdir.py" check "$DIR_IN")" || exit 3
K="$DIR/kopien"
[ -d "$K/shots" ] || { echo "kein kopien/shots in $DIR - erst capture.mjs, dann tile.sh <arbeitsordner>" >&2; exit 3; }
mkdir -p "$K/tiles" "$K/sheets"
# Reste eines frueheren Laufs entfernen, sonst mischen sich alte Kacheln und Boegen unter die neuen
find "$K/tiles" -maxdepth 1 -type f -name '*_t[0-9][0-9].png' -delete
find "$K/sheets" -maxdepth 1 -type f -name 'sheet_*' -delete

n_tiles=0; n_tile_err=0
while IFS= read -r -d '' f; do
  read -r w h < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$f" | tr x ' ')
  if [ -z "${w:-}" ]; then n_tile_err=$((n_tile_err+1)); echo "nicht lesbar: ${f#"$K/"}" >&2; continue; fi
  if [ "$w" -gt "$MAX_W" ]; then sh=$(( h * MAX_W / w )); sw=$MAX_W; else sh=$h; sw=$w; fi
  rel="${f#"$K/shots/"}"; base="${rel//\//_}"; base="${base%.png}"
  i=0
  for (( y=0; y<sh; y+=MAX_H )); do
    th=$(( sh - y < MAX_H ? sh - y : MAX_H ))
    out=$(printf '%s/tiles/%s_t%02d.png' "$K" "$base" "$i")
    if ffmpeg -nostdin -v error -y -i "$f" -vf "scale=${sw}:${sh},crop=${sw}:${th}:0:${y}" "$out"; then
      n_tiles=$((n_tiles+1))
    else
      n_tile_err=$((n_tile_err+1))
    fi
    i=$((i+1))
  done
done < <(find "$K/shots" -name '*.png' -print0 2>/dev/null | sort -z)

# Thumbnail einheitlich als RGBA, sonst bricht der tile-Filter bei wechselndem Pixelformat ab
thumb() { ffmpeg -nostdin -v error -y -i "$1" -frames:v 1 -vf "scale=${THUMB}:${THUMB}:force_original_aspect_ratio=decrease,pad=${THUMB}:${THUMB}:(ow-iw)/2:(oh-ih)/2:color=white,format=rgba" "$2" 2>/dev/null; }
# sharp aus ~/.local/share/site-anatomy liest aus einem Buffer: SVG laedt so keine Nachbardateien nach
SHARP_JS="
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const [tool, src, dst, max] = process.argv.slice(1);
const { loadTool } = await import(pathToFileURL(tool).href);
const { default: sharp } = await loadTool('sharp');
try {
  await sharp(readFileSync(src)).resize(Number(max), Number(max), { fit: 'inside', withoutEnlargement: true }).png().toFile(dst);
} catch (e) { console.error(e.message); process.exit(1); }
"
to_png() { node --input-type=module -e "$SHARP_JS" -- "$HERE/_tool.mjs" "$1" "$2" "$SHARP_MAX" 2>"$T/sharp.err"; }

n_sheets=0; k=0; via_sharp=0; skipped=0
if [ -d "$K/images" ]; then
  T=$(mktemp -d); trap 'rm -r "$T"' EXIT
  : > "$T/names"
  while IFS= read -r -d '' img; do
    name="${img##*/}"
    case "$name" in *.bin|*.json|*.txt) continue;; esac
    out=$(printf '%s/%04d.png' "$T" "$k")
    if ! thumb "$img" "$out"; then
      if to_png "$img" "$T/conv.png" && thumb "$T/conv.png" "$out"; then
        via_sharp=$((via_sharp+1))
      else
        skipped=$((skipped+1)); echo "uebersprungen: $name ($(tr '\n' ' ' < "$T/sharp.err" | cut -c1-200))" >&2
        continue
      fi
    fi
    printf '%s\n' "$name" >> "$T/names"; k=$((k+1))
  done < <(find "$K/images" -maxdepth 1 -type f -print0 | sort -z)
  if [ "$k" -gt 0 ]; then
    # -vsync statt -fps_mode: ffmpeg 4.4 auf netcup kennt -fps_mode nicht; Boegen zaehlen ab 01
    ffmpeg -nostdin -v error -y -framerate 1 -i "$T/%04d.png" -vf "tile=${COLS}x${ROWS}:color=white" -vsync passthrough -start_number 1 "$K/sheets/sheet_%02d.png"
    per=$((COLS*ROWS)); i=0
    while IFS= read -r name; do
      list=$(printf '%s/sheets/sheet_%02d.txt' "$K" $(( i / per + 1 )))
      [ -f "$list" ] || printf '# zeile\tspalte\tdatei (kopien/images/)\n' > "$list"
      printf '%d\t%d\t%s\n' $(( i % per / COLS + 1 )) $(( i % COLS + 1 )) "$name" >> "$list"
      i=$((i+1))
    done < "$T/names"
    n_sheets=$(find "$K/sheets" -name 'sheet_*.png' | wc -l)
  fi
else
  echo "kein kopien/images - Kontaktboegen entstehen erst nach measure.mjs" >&2
fi
[ "$n_sheets" -gt 0 ] || echo "WARNUNG: 0 Kontaktboegen - Bildsprache (Phase 3) hat kein Material" >&2
echo "Kacheln: $n_tiles (Fehler: $n_tile_err), Kontaktboegen: $n_sheets (aus $k Bildern, $via_sharp ueber sharp, $skipped uebersprungen)"
