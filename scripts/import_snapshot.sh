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

if [ -f "$SNAP/ollama-models.tar.gz" ]; then
  echo "[4/4] Found Ollama models in snapshot."
  if command -v ollama >/dev/null 2>&1; then
    echo "  Unpacking into ~/.ollama (recommended on macOS — Metal acceleration)..."
    mkdir -p "$HOME/.ollama"
    tar xzf "$SNAP/ollama-models.tar.gz" -C "$HOME/.ollama/"
    echo "  Done. Restart Ollama if needed (brew services restart ollama)."
  else
    echo "  Ollama not installed on host. For container-based Ollama:"
    echo "    mkdir -p data/ollama"
    echo "    tar xzf $SNAP/ollama-models.tar.gz -C data/ollama/"
    echo "    docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d"
  fi
fi

echo
echo "Done. Next steps:"
echo "  cd $TARGET && docker compose up -d --build"
echo "  → http://localhost:5173"
