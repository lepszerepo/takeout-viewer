#!/usr/bin/env bash
# Re-import every dataset already present in the database, in name order.
#
# Use this after you change a parser or schema — existing data stays,
# duplicates are detected by stable_hash, only NEW events are inserted.
#
# Usage:
#   API_URL=http://localhost:8001 ./scripts/reimport_all.sh
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-http://localhost:8001}"
LOG="$ROOT_DIR/data/logs/reimport_all.log"

mkdir -p "$(dirname "$LOG")"
echo "=== Re-import started at $(date) ===" | tee -a "$LOG"

# Fetch dataset names from the API
USERS=$(curl -s "$API_URL/api/datasets" | python3 -c "
import json, sys
for d in json.load(sys.stdin):
    print(d['name'])
")
if [ -z "$USERS" ]; then
  echo "No datasets in API (have you imported anything yet?)" | tee -a "$LOG"
  exit 1
fi

for user in $USERS; do
  echo "[$user] $(date +%H:%M:%S) starting" | tee -a "$LOG"
  RESP=$(curl -s -X POST "$API_URL/api/datasets/${user}/import" --max-time 28800)
  echo "[$user] $(date +%H:%M:%S) $RESP" | tee -a "$LOG"
done
echo "=== Re-import finished at $(date) ===" | tee -a "$LOG"
