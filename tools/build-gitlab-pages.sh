#!/usr/bin/env bash
# Build the public Kodi repository consumed by GitLab Pages.
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pages_url="${1:?Usage: build-gitlab-pages.sh <GitLab-Pages-URL>}"

python3 "$project_dir/tools/build_repo.py" \
    --out "$project_dir/public" --pages-url "${pages_url%/}"
