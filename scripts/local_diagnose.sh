#!/usr/bin/env bash
# Local helper to feed a GitHub Actions failed run into the debugger container.
# Usage: ./scripts/local_diagnose.sh [owner/repo] [run_id]
# If arguments are omitted, the script prompts for them.
# Requires:
#   • gh CLI authenticated (gh auth login)
#   • .env file in project root containing OPENAI_API_KEY=...
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.."; pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f .env ]]; then
  echo "❌  .env file not found in project root. Create one with model keys, e.g.:" >&2
  echo "OPENAI_API_KEY=sk-..." >&2
  exit 1
fi

REPO=${1-}
RUN_ID=${2-}

if [[ -z "$REPO" ]]; then
  read -rp "GitHub repository (owner/name): " REPO
fi
if [[ -z "$RUN_ID" ]]; then
  read -rp "Workflow run ID: " RUN_ID
fi

LOG_ARCHIVE="logs_${RUN_ID}.tar.gz"

echo "📥 Fetching logs for run $RUN_ID ..."
# -O writes to filename derived from URL; use -o for custom name
# Use --output to respect gh 2.x

gh api \
  "/repos/${REPO}/actions/runs/${RUN_ID}/logs" \
  --output "$LOG_ARCHIVE"

echo "🛠️  Ensuring debugger image exists..."
if ! docker image inspect fw-debugger:latest >/dev/null 2>&1; then
  docker build -t fw-debugger .
fi

echo "🚀 Running debugger container..."
docker run --rm \
  --env-file .env \
  -v "$(pwd)/$LOG_ARCHIVE:/tmp/logs.tar.gz" \
  fw-debugger \
  python /app/main.py /tmp/logs.tar.gz
