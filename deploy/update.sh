#!/usr/bin/env bash
# FlatBot — pull latest code and restart services
# Usage: bash deploy/update.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Pulling latest code..."
git pull --ff-only

echo "==> Rebuilding images..."
docker compose build --pull

echo "==> Restarting services (zero-downtime web, then bot)..."
docker compose up -d --no-deps web
docker compose up -d --no-deps bot

echo "==> Done."
docker compose ps
