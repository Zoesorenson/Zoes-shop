#!/usr/bin/env bash
set -euo pipefail

# Update Depop listings and commit the refreshed feed to main.
# Optional env vars:
#   PYTHON_BIN          Python executable to run (default: python3)
#   PUSH_AFTER_COMMIT   If set to 1, push the new commit to origin/main.
#
# This script respects DEPOP_USERNAME / DEPOP_COOKIE / DEPOP_COOKIE_FILE /
# DEPOP_DISABLE_PROXY for authentication and proxy control inside
# scripts/fetch_depop.py.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN is not available. Install Python 3 or set PYTHON_BIN." >&2
  exit 1
fi

echo "Fetching Depop products..."
"$PYTHON_BIN" scripts/fetch_depop.py

git_status=$(git rev-parse --abbrev-ref HEAD)
if [[ "$git_status" != "main" ]]; then
  echo "Error: current branch is '$git_status'. Switch to 'main' before committing." >&2
  exit 1
fi

if git diff --quiet -- data/products.json; then
  echo "No changes to commit."
  exit 0
fi

git add data/products.json
commit_msg="chore: refresh depop feed"

git commit -m "$commit_msg"
echo "Committed updated feed to main."

if [[ "${PUSH_AFTER_COMMIT:-}" == "1" ]]; then
  echo "Pushing to origin/main..."
  git push origin main
fi
