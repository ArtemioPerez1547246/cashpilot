#!/usr/bin/env bash
# Run ON the Linode after every working feature:  ./deploy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only
cd deploy
[ -f .env ] || { echo "Missing deploy/.env (copy .env.example and fill it in)"; exit 1; }
docker compose --env-file .env up -d --build
sleep 3
curl -fsS "https://$(grep '^DOMAIN=' .env | cut -d= -f2)/api/health" && echo " <- deployed OK"
