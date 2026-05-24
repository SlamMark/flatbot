#!/usr/bin/env bash
# FlatBot — first-time setup on a Proxmox LXC (Debian 12 / Ubuntu 22.04)
# Usage: bash deploy/install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Installing Docker..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "==> Enabling Docker..."
systemctl enable --now docker

echo "==> Creating /data directory..."
mkdir -p /data/backups

echo "==> Checking .env..."
if [ ! -f "$REPO_DIR/.env" ]; then
  cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
  echo "    Created .env from .env.example — EDIT IT before starting!"
fi

echo "==> Building and starting services..."
cd "$REPO_DIR"
docker compose build --pull
docker compose up -d

echo ""
echo "Done! Services:"
docker compose ps
echo ""
echo "Portal:  http://$(hostname -I | awk '{print $1}'):8000"
echo "Logs:    docker compose logs -f"
