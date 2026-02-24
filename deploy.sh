#!/usr/bin/env bash
# ============================================================
# deploy.sh — Build and deploy to vps2 via Docker context
# ============================================================
set -euo pipefail

COMPOSE_PROJECT="skirts-history"
PREVIOUS_CONTEXT="$(docker context show)"

cleanup() {
  echo ""
  echo "Restoring Docker context to: ${PREVIOUS_CONTEXT}"
  docker context use "${PREVIOUS_CONTEXT}"
}
trap cleanup EXIT

echo "=================================================="
echo "  Deploying: The History of the Skirt"
echo "  Target:    vps2"
echo "=================================================="
echo ""

# Switch to remote context
echo "[1/3] Switching Docker context to vps2..."
docker context use vps2

# Build and deploy
echo "[2/3] Building image and starting containers..."
docker compose -p "${COMPOSE_PROJECT}" up -d --build --remove-orphans

# Verify
echo "[3/3] Verifying deployment..."
docker compose -p "${COMPOSE_PROJECT}" ps

echo ""
echo "  Deploy complete."
echo "  Site is live on port 80 of vps2."
echo "=================================================="
