#!/usr/bin/env bash
set -euo pipefail

# local_diagnose.sh - Fetches failed workflow logs and runs the debugger agent locally.
#
# Usage:
#   ./scripts/local_diagnose.sh [OWNER/REPO] [RUN_ID]
#
# Environment variables:
#   OPENAI_API_KEY: Your OpenAI API key.
#   LLM_MODEL: The model to use (e.g., openai/gpt-4-turbo).
#
# The script can also read these from a .env file in the project root.

# --- Sanity checks ---
if ! command -v gh &> /dev/null; then
    echo "Error: gh (GitHub CLI) is not installed. See https://cli.github.com/" >&2
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed." >&2
    exit 1
fi

if [ $# -ne 2 ]; then
    echo "Usage: $0 OWNER/REPO RUN_ID" >&2
    exit 1
fi

REPO=$1
RUN_ID=$2
LOG_ARCHIVE_NAME="logs_${RUN_ID}.tar.gz"
IMAGE_NAME="fw-debugger"

# --- Log fetching ---
echo "📥 Fetching logs for run $RUN_ID ..."
LOG_ARCHIVE_NAME="logs_${RUN_ID}.tar.gz"

# Use GitHub API to download the combined run logs archive directly (tar.gz format)
if ! gh api "/repos/$REPO/actions/runs/$RUN_ID/logs" > "$LOG_ARCHIVE_NAME"; then
    echo "❌ Error: Failed to download workflow run logs for run $RUN_ID." >&2
    echo "Check that the run ID is valid and you have access to the repository." >&2
    exit 1
fi

echo "✅ Logs downloaded to $LOG_ARCHIVE_NAME"

# --- Docker build ---
echo "🛠️  Ensuring debugger image exists..."
docker build -t "$IMAGE_NAME" . > /dev/null

# --- Docker run ---
# Prepare Docker arguments
DOCKER_RUN_CMD="docker run --rm"

# Check for .env file first, otherwise use environment variables from the shell
if [ -f ".env" ]; then
    echo "Found .env file, using it for environment variables."
    DOCKER_RUN_CMD="$DOCKER_RUN_CMD --env-file .env"
elif [ -n "${OPENAI_API_KEY:-}" ]; then
    echo "Using shell environment variables for configuration."
    DOCKER_RUN_CMD="$DOCKER_RUN_CMD --env OPENAI_API_KEY=${OPENAI_API_KEY}"
    if [ -n "${LLM_MODEL:-}" ]; then
        DOCKER_RUN_CMD="$DOCKER_RUN_CMD --env LLM_MODEL=${LLM_MODEL}"
    fi
else
    echo "❌ Error: OPENAI_API_KEY not set and no .env file found." >&2
    exit 1
fi

# Add volume mount and the rest of the command
DOCKER_RUN_CMD="$DOCKER_RUN_CMD -v $PWD/$LOG_ARCHIVE_NAME:/tmp/logs.tar.gz $IMAGE_NAME /tmp/logs.tar.gz"

echo "🚀 Running debugger container..."
# Use eval to ensure the command string with all its arguments is parsed correctly
eval "$DOCKER_RUN_CMD"
