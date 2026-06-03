#!/usr/bin/env bash
# Unpack a Takeout Viewer snapshot prepared with export_snapshot.sh.
# Usage:
#   ./import_snapshot.sh <SNAPSHOT_DIR> [TARGET_DIR]
set -eu

SNAP="${1:-}"
TARGET="${2:-$(pwd)/takeout-viewer}"
if [ -z "$SNAP" ] || [ ! -d "$SNAP" ]; then
  echo "Usage: $0 <SNAPSHOT_DIR> [TARGET_DIR]"
  exit 1
fi

echo "Snapshot: $SNAP"
echo "Target:   $TARGET"
mkdir -p "$TARGET" && cd "$TARGET"

echo "[1/3] Unpacking code..."
tar xzf "$SNAP/takeout-viewer-code.tar.gz"

mkdir -p data
echo "[2/3] Unpacking DB..."
[ -f "$SNAP/takeout-viewer-db.tar.gz" ] && tar xzf "$SNAP/takeout-viewer-db.tar.gz" -C data/ || echo "  no DB in snapshot"

echo "[3/3] Unpacking attachments..."
[ -f "$SNAP/takeout-viewer-attachments.tar.gz" ] && tar xzf "$SNAP/takeout-viewer-attachments.tar.gz" -C data/ || echo "  no attachments in snapshot"

mkdir -p data/imports data/logs

echo
echo "Done. Next steps:"
echo "  1) (optional) set up Ollama — see $SNAP/SETUP.md section 'Local AI'"
echo "  2) cd $TARGET && docker compose up -d --build"
echo "  3) http://localhost:5173"
