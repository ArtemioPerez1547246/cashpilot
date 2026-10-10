#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --ff-only

docker compose -f deploy/docker-compose.yml up -d --build
