#!/usr/bin/env bash
# Sequential extract + import of multiple Google Takeout exports.
#
# Usage:
#   SRC_BASE=/path/to/takeout-zips ./scripts/bulk_import.sh
#
# Optional env vars:
#   SRC_BASE   — directory containing per-user subdirs with takeout .zip files
#                (default: ./takeout-sources/)
#   DST_BASE   — where to extract (default: ./data/imports/)
#   API_URL    — backend URL (default: http://localhost:8001)
#
# It expects a layout like:
#   <SRC_BASE>/<USER>/takeout-*.zip
# and will extract each user's zips into <DST_BASE>/<USER>/ then call the
# backend import endpoint for that user.
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_BASE="${SRC_BASE:-$ROOT_DIR/takeout-sources}"
DST_BASE="${DST_BASE:-$ROOT_DIR/data/imports}"
API_URL="${API_URL:-http://localhost:8001}"
LOG="$ROOT_DIR/data/logs/bulk_import.log"

mkdir -p "$DST_BASE" "$(dirname "$LOG")"

if [ ! -d "$SRC_BASE" ]; then
  echo "Source directory not found: $SRC_BASE" >&2
  echo "Set SRC_BASE env var or create the directory with subfolders per user." >&2
  exit 1
fi

echo "=== Bulk import started at $(date) ===" | tee -a "$LOG"
echo "    SRC_BASE=$SRC_BASE" | tee -a "$LOG"
echo "    DST_BASE=$DST_BASE" | tee -a "$LOG"

for user_dir in "$SRC_BASE"/*/; do
  [ -d "$user_dir" ] || continue
  user="$(basename "$user_dir")"
  # Sanitize: keep alnum + . _ -
  slug="$(echo "$user" | tr -cd '[:alnum:]._-')"
  if [ -z "$slug" ]; then
    echo "[skip] $user — name becomes empty after sanitization" | tee -a "$LOG"
    continue
  fi
  DST="$DST_BASE/$slug"
  if [ -d "$DST/Takeout" ]; then
    echo "[$slug] already extracted, skipping extract" | tee -a "$LOG"
  else
    mkdir -p "$DST"
    n_zip=$(ls "$user_dir"/*.zip 2>/dev/null | wc -l | tr -d ' ')
    echo "[$slug] extracting $n_zip zip files..." | tee -a "$LOG"
    for z in "$user_dir"/*.zip; do
      [ -f "$z" ] || continue
      echo "  - $(basename "$z")" | tee -a "$LOG"
      unzip -q -o "$z" -d "$DST" 2>>"$LOG"
    done
  fi

  echo "[$slug] starting import..." | tee -a "$LOG"
  RESP=$(curl -s -X POST "$API_URL/api/datasets/${slug}/import" --max-time 28800)
  echo "[$slug] $RESP" | tee -a "$LOG"
done

echo "=== Bulk import finished at $(date) ===" | tee -a "$LOG"
