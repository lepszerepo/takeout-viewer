#!/usr/bin/env bash
# Package a self-contained snapshot of Takeout Viewer for sharing on a USB/NAS.
#
# Produces a directory:
#   <OUT>/
#     takeout-viewer-code.tar.gz       — application source (from current dir)
#     takeout-viewer-db.tar.gz         — SQLite DB (all parsed knowledge)
#     takeout-viewer-attachments.tar.gz — mail attachment binaries
#     ollama-models/                   — optional, copied LLM model blobs
#     SETUP.md                         — recipient instructions
#
# Usage:
#   ./scripts/export_snapshot.sh [OUTPUT_DIR] [--with-models]
#
# Defaults to ./snapshot-YYYYMMDD/
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="${1:-./snapshot-$(date +%Y%m%d)}"
WITH_MODELS=0
if [ "${2:-}" = "--with-models" ] || [ "${1:-}" = "--with-models" ]; then
  WITH_MODELS=1
fi
if [ "$OUT_DIR" = "--with-models" ]; then
  OUT_DIR="./snapshot-$(date +%Y%m%d)"
fi

echo "Output directory: $OUT_DIR"
mkdir -p "$OUT_DIR"

# 1. Code (everything except data/, node_modules, .git, venvs, caches)
echo "[1/4] Packing application code..."
tar czf "$OUT_DIR/takeout-viewer-code.tar.gz" \
    --exclude='./data/imports' \
    --exclude='./data/db' \
    --exclude='./data/attachments' \
    --exclude='./data/logs' \
    --exclude='./data/cache' \
    --exclude='./frontend/node_modules' \
    --exclude='./backend/.venv-test' \
    --exclude='./backend/__pycache__' \
    --exclude='./.git' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    .

# 2. DB — contains all parsed mail bodies, entities, embeddings, topics
echo "[2/4] Packing SQLite database (this is the 'knowledge')..."
if [ ! -f "data/db/takeout_viewer.sqlite" ]; then
  echo "  ! No DB found — recipient will start empty"
else
  tar czf "$OUT_DIR/takeout-viewer-db.tar.gz" -C data db/
fi

# 3. Attachments (content-addressed binaries)
echo "[3/4] Packing mail attachments..."
if [ -d "data/attachments" ]; then
  ATT_COUNT=$(find data/attachments -type f | wc -l | tr -d ' ')
  ATT_SIZE=$(du -sh data/attachments | awk '{print $1}')
  echo "  $ATT_COUNT files, $ATT_SIZE"
  tar czf "$OUT_DIR/takeout-viewer-attachments.tar.gz" -C data attachments/
fi

# 4. Optional: Ollama models
if [ "$WITH_MODELS" = "1" ]; then
  echo "[4/4] Exporting Ollama models (LLM + embeddings)..."
  if [ -d "$HOME/.ollama/models" ]; then
    mkdir -p "$OUT_DIR/ollama-models"
    # Save just the two models we need (~9 GB)
    for model in "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M" "bge-m3:latest"; do
      slug=$(echo "$model" | tr '/:' '__')
      echo "  exporting $model -> $slug.tar"
      if command -v ollama >/dev/null 2>&1; then
        ollama show "$model" >/dev/null 2>&1 && {
          # Save raw blobs referenced by manifest
          tar cf "$OUT_DIR/ollama-models/$slug.tar" -C "$HOME/.ollama" "models" 2>/dev/null || true
        }
      fi
    done
    # Simpler approach: dump the whole .ollama/models dir (works on same OS/arch)
    echo "  saving full ~/.ollama/models snapshot (best for same-arch copy)..."
    tar czf "$OUT_DIR/ollama-models/ollama-models-full.tar.gz" -C "$HOME/.ollama" models/
  else
    echo "  ~/.ollama not found, skipping"
  fi
else
  echo "[4/4] Skipping Ollama models (use --with-models to include)."
  echo "       Recipient can also just run: ollama pull <model> (needs internet)"
fi

# 5. Setup notes for recipient
cat > "$OUT_DIR/SETUP.md" <<'EOF'
# Takeout Viewer — Snapshot Setup

This directory is a complete, portable knowledge snapshot. After unpacking
on a new machine you have the same parsed data, embeddings, entities,
topics, etc. as the original installation.

## Quick start

```bash
# 1. Pick a working directory
mkdir takeout-viewer && cd takeout-viewer

# 2. Unpack code
tar xzf <PATH_TO_SNAPSHOT>/takeout-viewer-code.tar.gz

# 3. Unpack data
mkdir -p data
tar xzf <PATH_TO_SNAPSHOT>/takeout-viewer-db.tar.gz -C data/
tar xzf <PATH_TO_SNAPSHOT>/takeout-viewer-attachments.tar.gz -C data/

# 4. Bring up the stack
docker compose up -d --build

# 5. Open http://localhost:5173
```

## Local AI (Ollama) — required for LLM/semantic search

If you already have `ollama` running on host with the models, skip this.
Otherwise pick ONE option:

### Option A — Install Ollama natively (RECOMMENDED on macOS / Linux)

```bash
# Mac:
brew install ollama && brew services start ollama
# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Pull models (~9 GB total)
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
ollama pull bge-m3:latest
```

### Option B — Restore models from this snapshot (if included)

```bash
# Stop ollama
brew services stop ollama 2>/dev/null || sudo systemctl stop ollama 2>/dev/null

mkdir -p ~/.ollama
tar xzf <PATH_TO_SNAPSHOT>/ollama-models/ollama-models-full.tar.gz -C ~/.ollama/

# Restart ollama
brew services start ollama 2>/dev/null || sudo systemctl start ollama 2>/dev/null
```

### Option C — Run Ollama in a Docker container (slower, no Metal)

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d
docker exec takeout-viewer-ollama ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
docker exec takeout-viewer-ollama ollama pull bge-m3:latest
```

## What works without Ollama

Even without local LLM, you still get:
- Full event timeline, filters, threading
- Mail folders, threads, attachments download
- **FTS5** full-text search with BM25
- **NER**-based entity browsing (already pre-computed in the DB)
- Graph of correspondents
- Person profile pages
- Anomaly signals

Only the AI summary / classify / semantic search require Ollama.
EOF

# Summary
echo
echo "Snapshot ready at: $OUT_DIR"
echo
echo "Sizes:"
ls -lh "$OUT_DIR"/*.tar.gz 2>/dev/null | awk '{print "  ",$5,$9}'
TOTAL=$(du -sh "$OUT_DIR" | awk '{print $1}')
echo "Total: $TOTAL"
echo
echo "Hand this directory to the recipient via USB / NAS / Tailscale send / etc."
